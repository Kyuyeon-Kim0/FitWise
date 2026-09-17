import json
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
from app.review_agent import analyze
from app.review_agent.qa_agent import answer as ask_review_qa
from app.services import ask_review_agent, browse_products, run_fit, run_review


class FitWiseTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = Path(self.directory.name) / "test.db"
        self.environment = patch.dict(os.environ, {"FITWISE_ANALYSIS_MODE": "baseline", "OPENAI_API_KEY": ""})
        self.environment.start()
        initialize(self.database)

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def test_seed_idempotent_and_foreign_keys(self):
        initialize(self.database)
        with connect(self.database) as connection:
            for table, expected in (("users", 20), ("products", 36), ("orders", 864)):
                self.assertEqual(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], expected)
            # 상품별 리뷰 수는 10~30건 사이 무작위이므로 범위와 상품별 최소치만 검증합니다.
            review_total = connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
            self.assertTrue(36 * 10 <= review_total <= 36 * 30)
            per_product = [row[0] for row in connection.execute(
                "SELECT COUNT(*) FROM reviews GROUP BY product_id")]
            self.assertEqual(len(per_product), 36)
            self.assertTrue(all(10 <= c <= 30 for c in per_product))
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO returns(order_id,reason,returned_at) VALUES (99999,'test','2026-09-01')")
            connection.rollback()
            order_id = connection.execute("SELECT order_id FROM returns LIMIT 1").fetchone()[0]
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO returns(order_id,reason,returned_at) VALUES (?,'test','2026-09-01')", (order_id,))

    def test_legacy_resource_logs_are_migrated_without_data_loss(self):
        with connect(self.database) as connection:
            connection.execute("DROP INDEX IF EXISTS idx_resources_operation")
            connection.execute("DROP INDEX IF EXISTS idx_resources_request")
            connection.execute("ALTER TABLE resource_logs RENAME TO resource_logs_current")
            connection.execute("""CREATE TABLE resource_logs (
                id INTEGER PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
                operation TEXT NOT NULL CHECK(operation IN ('browse','review','fit')),
                cpu_percent REAL NOT NULL, cpu_ms REAL NOT NULL,
                memory_before_mb REAL NOT NULL, memory_after_mb REAL NOT NULL,
                memory_delta_mb REAL NOT NULL, processing_ms REAL NOT NULL,
                response_ms REAL NOT NULL, status TEXT NOT NULL CHECK(status IN ('success','error')),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )""")
            connection.execute("""INSERT INTO resource_logs
                (request_id,operation,cpu_percent,cpu_ms,memory_before_mb,memory_after_mb,
                 memory_delta_mb,processing_ms,response_ms,status)
                VALUES ('legacy','browse',1,1,100,101,1,5,6,'success')""")
            connection.execute("DROP TABLE resource_logs_current")
            connection.commit()

        initialize(self.database, seed=False)

        with connect(self.database) as connection:
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(resource_logs)")}
            row = connection.execute(
                "SELECT request_id,phase,status FROM resource_logs WHERE request_id='legacy'"
            ).fetchone()
        self.assertIn("phase", columns)
        self.assertEqual(dict(row), {"request_id": "legacy", "phase": "completed", "status": "success"})

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
            connection.execute("DELETE FROM reviews")
            connection.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", [
                (1, 1, 1, "M", "2026-01-01"), (2, 1, 1, "M", "2026-01-02"),
                (3, 2, 1, "M", "2026-01-03")])
            connection.execute("INSERT INTO returns VALUES (1,2,'사이즈','2026-01-05')")
            connection.execute("INSERT INTO reviews(user_id,product_id,size,rating,content,created_at) VALUES (1,1,'M',5,'좋아요','2026-01-01')")
            connection.commit()
            review = analyze([{"rating": 5, "content": "좋아요"}])
            result = fit_analyze(connection, 1, get_product(connection, 1), "M", review, 165, 60)
        # 선택 사이즈 안정성은 체형 유사 구매 이력에 가중치를 둡니다.
        self.assertEqual(result["score"], 68)
        self.assertTrue(result["limited_data"])

    def test_missing_data_is_not_perfect_success(self):
        with connect(self.database) as connection:
            connection.execute("DELETE FROM returns")
            connection.execute("DELETE FROM orders")
            connection.execute("DELETE FROM reviews")
            connection.commit()
        result = run_fit(1, 1, "M", "레귤러핏", 165, 60, self.database)["result"]
        self.assertIsNone(result["score"])
        self.assertTrue(all(m["value"] is None for m in result["metrics"]))
        with connect(self.database) as connection:
            connection.execute("INSERT INTO reviews(user_id,product_id,size,rating,content,created_at) VALUES (1,1,'M',5,'좋아요','2026-01-01')")
            connection.execute("DELETE FROM review_analysis WHERE product_id=1")
            connection.commit()
        result = run_fit(1, 1, "M", "레귤러핏", 165, 60, self.database)["result"]
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["metrics"][-1]["effective_weight_pct"], 100)
        self.assertTrue(result["limited_data"])

    def test_filters_and_validation(self):
        self.assertEqual(len(browse_products("하의", self.database)), 12)
        for user_id, size, preferred_fit, height in ((1, "XXXL", "레귤러핏", 165), (999, "M", "레귤러핏", 165),
                                                      (True, "M", "레귤러핏", 165), (1, ["M"], "레귤러핏", 165),
                                                      (1, "M", "알 수 없음", 165), (1, "M", "레귤러핏", 130),
                                                      (1, "M", "레귤러핏", 210)):
            with self.assertRaises(ValueError):
                run_fit(1, user_id, size, preferred_fit, height, 60, self.database)
        with self.assertRaises(ValueError):
            run_review(999, self.database)
        with connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM agent_logs").fetchone()[0], 0)

    def test_pipeline_measurements_and_correlation(self):
        browse_products(database=self.database)
        run_review(1, self.database)
        saved = run_fit(1, 1, "M", "레귤러핏", 165, 60, self.database)
        with connect(self.database) as connection:
            data = dashboard_data(connection)
            agents = connection.execute("SELECT * FROM agent_logs WHERE request_id=?", (saved["request_id"],)).fetchall()
            resources = connection.execute("SELECT * FROM resource_logs WHERE request_id=?", (saved["request_id"],)).fetchall()
            self.assertEqual(len(agents), 2)
        self.assertEqual(len(resources), 2)
        self.assertEqual(data["counts"]["total"], 2)
        self.assertEqual({row["operation"] for row in data["summary"]}, {"browse", "review", "fit"})
        self.assertEqual({row["status"] for row in agents}, {"started", "success"})
        self.assertEqual({row["phase"] for row in resources}, {"requested", "completed"})
        row = next(row for row in resources if row["phase"] == "completed")
        self.assertGreaterEqual(row["response_ms"], row["processing_ms"])
        self.assertGreater(row["memory_after_mb"], 0)
        self.assertGreaterEqual(row["cpu_percent"], 0)
        self.assertLessEqual(row["cpu_percent"], 100)
        self.assertAlmostEqual(row["memory_delta_mb"], row["memory_after_mb"] - row["memory_before_mb"])

    def test_analysis_failure_is_logged(self):
        with patch("app.services.analyze_reviews", side_effect=RuntimeError("test failure")):
            with self.assertRaises(RuntimeError):
                run_fit(1, 1, "M", "레귤러핏", 165, 60, self.database)
        with connect(self.database) as connection:
            agents = connection.execute("SELECT status,error_type FROM agent_logs").fetchall()
            resources = connection.execute("SELECT phase,status FROM resource_logs").fetchall()
            data = dashboard_data(connection)
        self.assertEqual(len(agents), 4)
        self.assertEqual([row["status"] for row in agents].count("started"), 2)
        self.assertEqual([row["status"] for row in agents].count("error"), 2)
        self.assertEqual([(row["phase"], row["status"]) for row in resources],
                         [("requested", "started"), ("completed", "error")])
        self.assertEqual(data["summary"], [])

    @staticmethod
    def _tool_call(call_id, name, arguments):
        from unittest.mock import MagicMock
        call = MagicMock()
        call.id = call_id
        call.function.name = name
        call.function.arguments = json.dumps(arguments)
        return call

    @staticmethod
    def _respond_call(**fields):
        base = {"answer": "답변입니다.", "overall_stance": "mixed", "stance_reason": "근거",
               "fit_assessment": "unknown", "recommend_alternatives": False, "recommended_product_ids": []}
        base.update(fields)
        return FitWiseTest._tool_call("call_respond", "respond", base)

    def test_qa_agent_calls_tool_then_answers(self):
        from unittest.mock import MagicMock

        reviews = [{"rating": 2, "content": "허리가 작아서 불편해요.", "size": "M"},
                  {"rating": 5, "content": "착용감이 좋아요.", "size": "M"}]
        product = {"name": "테스트 상품", "category": "하의", "subcategory": "슬랙스",
                  "description": "설명", "sizes": ["S", "M", "L"], "measurements": {}}

        search_call = self._tool_call("call_1", "search_reviews", {"keyword": "허리"})
        first_response = MagicMock(choices=[MagicMock(message=MagicMock(content=None, tool_calls=[search_call]))])
        respond_call = self._respond_call(answer="허리가 작다는 리뷰가 1건 있습니다.", overall_stance="negative",
                                          fit_assessment="poor_fit", recommend_alternatives=True,
                                          recommended_product_ids=[7])
        final_response = MagicMock(choices=[MagicMock(message=MagicMock(content=None, tool_calls=[respond_call]))])

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [first_response, final_response]
        with patch("openai.OpenAI", return_value=mock_client):
            result = ask_review_qa("허리 사이즈 어때?", product, reviews, [], "fake-key", "fake-model")

        self.assertEqual(result["answer"], "허리가 작다는 리뷰가 1건 있습니다.")
        self.assertEqual(result["overall_stance"], "negative")
        self.assertEqual(result["fit_assessment"], "poor_fit")
        self.assertEqual(result["recommended_product_ids"], [7])
        self.assertEqual(result["tools_used"], ["search_reviews"])
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)

    def test_qa_agent_falls_back_to_sample_when_no_exact_keyword_match(self):
        import json
        from unittest.mock import MagicMock

        reviews = [{"rating": r, "content": f"리뷰 내용 {r}", "size": "M"}
                  for r in [5, 4, 3, 2, 1, 5, 4, 3, 2, 1, 5]]
        product = {"name": "테스트 상품", "category": "상의", "subcategory": "셔츠",
                  "description": "설명", "sizes": ["S", "M", "L"], "measurements": {}}

        search_call = self._tool_call("call_1", "search_reviews", {"keyword": "통기성"})
        first_response = MagicMock(choices=[MagicMock(message=MagicMock(content=None, tool_calls=[search_call]))])
        respond_call = self._respond_call(answer="통기성을 직접 언급한 리뷰는 없지만 참고할 만한 내용을 찾았어요.")
        final_response = MagicMock(choices=[MagicMock(message=MagicMock(content=None, tool_calls=[respond_call]))])

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [first_response, final_response]
        with patch("openai.OpenAI", return_value=mock_client):
            ask_review_qa("통기성 어때?", product, reviews, [], "fake-key", "fake-model")

        second_call_messages = mock_client.chat.completions.create.call_args_list[1].kwargs["messages"]
        tool_message = next(m for m in second_call_messages if m["role"] == "tool")
        payload = json.loads(tool_message["content"])
        self.assertFalse(payload["exact_match"])
        self.assertGreater(len(payload["reviews"]), 0)

    def test_qa_agent_recommends_alternatives_via_tool(self):
        from unittest.mock import MagicMock

        reviews = [{"rating": 1, "content": "사이즈가 안 맞아서 반품했어요. 허리가 너무 작아요.", "size": "S"}]
        product = {"name": "테스트 상품", "category": "하의", "subcategory": "슬랙스",
                  "description": "설명", "sizes": ["S", "M", "L"], "measurements": {}}
        catalog = [{"id": 7, "name": "대체 상품", "price": 50000, "subcategory": "슬랙스",
                   "rating": 4.5, "review_count": 10}]

        alt_call = self._tool_call("call_1", "find_alternative_products", {})
        first_response = MagicMock(choices=[MagicMock(message=MagicMock(content=None, tool_calls=[alt_call]))])
        respond_call = self._respond_call(fit_assessment="poor_fit", recommend_alternatives=True,
                                          recommended_product_ids=[7])
        final_response = MagicMock(choices=[MagicMock(message=MagicMock(content=None, tool_calls=[respond_call]))])

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [first_response, final_response]
        with patch("openai.OpenAI", return_value=mock_client):
            result = ask_review_qa("이거 안 맞으면 다른 거 추천해줘", product, reviews, catalog,
                                   "fake-key", "fake-model", size="S", height=170, weight=65)

        second_call_messages = mock_client.chat.completions.create.call_args_list[1].kwargs["messages"]
        tool_message = next(m for m in second_call_messages if m["role"] == "tool")
        self.assertIn("대체 상품", tool_message["content"])
        self.assertEqual(result["recommended_product_ids"], [7])
        self.assertTrue(result["recommend_alternatives"])

    def test_qa_agent_requires_question(self):
        with self.assertRaises(LLMError):
            ask_review_qa("   ", {}, [], [], "fake-key", "fake-model")

    def test_ask_review_agent_requires_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with self.assertRaises(ValueError):
                ask_review_agent(1, "허리 사이즈 어때?", self.database)
        with connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM agent_logs").fetchone()[0], 0)

    def test_ask_review_agent_failure_is_logged(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key", "OPENAI_MODEL": "fake-model"}):
            with patch("app.services.ask_review_qa", side_effect=LLMError("timeout")):
                with self.assertRaises(LLMError):
                    ask_review_agent(1, "허리 사이즈 어때?", self.database)
        with connect(self.database) as connection:
            agents = connection.execute("SELECT status FROM agent_logs").fetchall()
        self.assertEqual([row["status"] for row in agents], ["started", "error"])


if __name__ == "__main__":
    unittest.main()
