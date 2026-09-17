import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.db import connect, initialize
from app.fit_agent import analyze as fit_analyze
from app.llm import LLMError
from app.monitoring import dashboard_data
from app.repository import get_product
from app.review_agent import analyze, analyze_api
from app.services import browse_products, run_fit, run_review


class FitWiseTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = Path(self.directory.name) / "test.db"
        self.environment = patch.dict(os.environ, {"FITWISE_ANALYSIS_MODE": "baseline"})
        self.environment.start()
        initialize(self.database)

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def test_seed_idempotent_and_foreign_keys(self):
        initialize(self.database)
        with connect(self.database) as connection:
            for table, expected in (("users", 3), ("products", 6), ("orders", 144), ("reviews", 48)):
                self.assertEqual(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], expected)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO returns(order_id,reason,returned_at) VALUES (99999,'test','2026-09-01')")
            connection.rollback()
            order_id = connection.execute("SELECT order_id FROM returns LIMIT 1").fetchone()[0]
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO returns(order_id,reason,returned_at) VALUES (?,'test','2026-09-01')", (order_id,))

    def test_review_counts_and_empty(self):
        result = analyze([{"rating": 5, "content": "편안해요. 편안해요."},
                          {"rating": 3, "content": "소재가 얇아요."},
                          {"rating": 1, "content": "사이즈가 커요. 소매가 길어요."},
                          {"rating": 4, "content": "핏이 좋아요."}])
        self.assertEqual(result["positive_pct"], 50)
        self.assertEqual(result["neutral_pct"], 25)
        self.assertEqual(result["negative_pct"], 25)
        self.assertEqual(result["size_complaint_pct"], 25)
        self.assertEqual(result["positive_keywords"][0]["count"], 1)
        self.assertIsNone(analyze([])["positive_pct"])

    def test_review_negation_and_extended_keywords(self):
        result = analyze([
            {"rating": 5, "content": "디자인이 예쁘지 않아요. 그래도 재질은 괜찮아요."},
            {"rating": 5, "content": "하나도 안 편안해요."},
            {"rating": 4, "content": "허리가 커서 벨트가 필요해요."},
            {"rating": 4, "content": "착용감은 편안한데 사이즈가 작아요."},
        ])
        self.assertEqual(result["positive_keywords"], [{"keyword": "착용감", "count": 1}])
        negative_labels = {item["keyword"] for item in result["negative_keywords"]}
        self.assertIn("허리 큼", negative_labels)
        self.assertIn("사이즈 작음", negative_labels)
        # 허리 불만은 계약(CONTRACTS.md)의 size_complaint_pct 계산 대상이 아니므로
        # 사이즈 작음 리뷰 1건만 반영되어 4건 중 25%여야 합니다.
        self.assertEqual(result["size_complaint_pct"], 25)

    def test_incompatible_database_is_preserved(self):
        old_path = Path(self.directory.name) / "old.db"
        with connect(old_path) as connection:
            connection.execute("CREATE TABLE users (user_id INTEGER PRIMARY KEY, name TEXT)")
            connection.execute("INSERT INTO users VALUES (1,'existing')")
            connection.commit()
        with self.assertRaises(ValueError):
            initialize(old_path)
        with connect(old_path) as connection:
            self.assertEqual(connection.execute("SELECT name FROM users").fetchone()[0], "existing")
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0], 1)

    def test_hand_calculated_fit(self):
        # 사용자 1: 동일 카테고리 M 성공 1 / 반품 1; 다른 사용자 M 성공 1.
        with connect(self.database) as connection:
            connection.execute("DELETE FROM returns")
            connection.execute("DELETE FROM orders")
            connection.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", [
                (1, 1, 1, "M", "2026-01-01"), (2, 1, 1, "M", "2026-01-02"),
                (3, 2, 1, "M", "2026-01-03")])
            connection.execute("INSERT INTO returns VALUES (1,2,'사이즈','2026-01-05')")
            connection.commit()
            review = analyze([{"rating": 5, "content": "좋아요"}])
            result = fit_analyze(connection, 1, get_product(connection, 1), "M", review)
        # 50*.30 + 66.7*.20 + 66.7*.25 + 100*.25 = 70.015
        self.assertEqual(result["score"], 70)
        self.assertEqual(result["metrics"][2]["value"], 66.7)
        self.assertTrue(result["limited_data"])

    def test_missing_data_is_not_perfect_success(self):
        with connect(self.database) as connection:
            connection.execute("DELETE FROM returns")
            connection.execute("DELETE FROM orders")
            connection.execute("DELETE FROM reviews")
            connection.commit()
        result = run_fit(1, 1, "M", self.database)["result"]
        self.assertIsNone(result["score"])
        self.assertTrue(all(m["value"] is None for m in result["metrics"]))
        with connect(self.database) as connection:
            connection.execute("INSERT INTO reviews(user_id,product_id,size,rating,content,created_at) VALUES (1,1,'M',5,'좋아요','2026-01-01')")
            connection.execute("DELETE FROM review_analysis WHERE product_id=1")
            connection.commit()
        result = run_fit(1, 1, "M", self.database)["result"]
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["metrics"][-1]["effective_weight_pct"], 100)
        self.assertTrue(result["limited_data"])

    def test_filters_and_validation(self):
        self.assertEqual(len(browse_products("하의", self.database)), 2)
        for user_id, size in ((1, "XXXL"), (999, "M"), (True, "M"), (1, ["M"])):
            with self.assertRaises(ValueError):
                run_fit(1, user_id, size, self.database)
        with self.assertRaises(ValueError):
            run_review(999, self.database)
        with connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM agent_logs").fetchone()[0], 0)

    def test_pipeline_measurements_and_correlation(self):
        browse_products(database=self.database)
        run_review(1, self.database)
        saved = run_fit(1, 1, "M", self.database)
        with connect(self.database) as connection:
            data = dashboard_data(connection)
            agents = connection.execute("SELECT * FROM agent_logs WHERE request_id=?", (saved["request_id"],)).fetchall()
            resources = connection.execute("SELECT * FROM resource_logs WHERE request_id=?", (saved["request_id"],)).fetchall()
            self.assertEqual(len(agents), 1)
        self.assertEqual(len(resources), 1)
        self.assertEqual(data["counts"]["total"], 2)
        self.assertEqual({row["operation"] for row in data["summary"]}, {"browse", "review", "fit"})
        row = resources[0]
        self.assertGreaterEqual(row["response_ms"], row["processing_ms"])
        self.assertGreater(row["memory_after_mb"], 0)
        self.assertGreaterEqual(row["cpu_percent"], 0)
        self.assertAlmostEqual(row["memory_delta_mb"], row["memory_after_mb"] - row["memory_before_mb"])

    def test_analysis_failure_is_logged(self):
        with patch("app.services.analyze_reviews", side_effect=RuntimeError("test failure")):
            with self.assertRaises(RuntimeError):
                run_fit(1, 1, "M", self.database)
        with connect(self.database) as connection:
            agents = connection.execute("SELECT status,error_type FROM agent_logs").fetchall()
            resource = connection.execute("SELECT status FROM resource_logs").fetchone()
            data = dashboard_data(connection)
        self.assertEqual(len(agents), 2)
        self.assertTrue(all(row["status"] == "error" for row in agents))
        self.assertEqual(resource["status"], "error")
        self.assertEqual(data["summary"], [])

    def test_analyze_api_ignores_unknown_labels_and_indices(self):
        reviews = [{"rating": 5, "content": "착용감이 좋아요."}, {"rating": 1, "content": "사이즈가 커요."}]
        fake_response = [
            {"index": 0, "positive_labels": ["착용감", "존재하지않는라벨"], "negative_labels": []},
            {"index": 1, "positive_labels": [], "negative_labels": ["사이즈 큼"]},
            {"index": 99, "positive_labels": ["마감"], "negative_labels": []},
        ]
        with patch("app.review_agent.classify_reviews", return_value=fake_response) as mock_classify:
            result = analyze_api(reviews, "fake-key", "fake-model")
        mock_classify.assert_called_once()
        self.assertEqual(result["mode"], "api-fake-model")
        self.assertEqual(result["positive_keywords"], [{"keyword": "착용감", "count": 1}])
        self.assertEqual(result["negative_keywords"], [{"keyword": "사이즈 큼", "count": 1}])
        self.assertEqual(result["size_complaint_pct"], 50)

    def test_run_review_api_requires_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with self.assertRaises(ValueError):
                run_review(1, self.database, mode="api")
        with connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM agent_logs").fetchone()[0], 0)

    def test_run_review_api_failure_is_logged(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key", "OPENAI_MODEL": "fake-model"}):
            with patch("app.services.analyze_reviews_api", side_effect=LLMError("timeout")):
                with self.assertRaises(LLMError):
                    run_review(1, self.database, mode="api")
        with connect(self.database) as connection:
            agents = connection.execute("SELECT status FROM agent_logs").fetchall()
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["status"], "error")


if __name__ == "__main__":
    unittest.main()
