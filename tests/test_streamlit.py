import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.config import ROOT
from app.db import connect


class StreamlitFlowTest(unittest.TestCase):
    def test_user_flow_and_no_agent_on_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / "ui.db")
            with patch.dict(os.environ, {"FITWISE_DB_PATH": database, "OPENAI_API_KEY": "",
                                        "FITWISE_ANALYSIS_MODE": "baseline"}):
                app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
                self.assertEqual(len(app.exception), 0)
                app.radio(key="category").set_value("하의").run()
                self.assertEqual(len(app.exception), 0)
                app.button(key="product_3").click().run()
                self.assertEqual(len(app.exception), 0)
                # AppTest는 st.switch_page로 전환한 뒤 다음 run의 page hash를
                # 자동 유지하지 않으므로 테스트 대상을 명시합니다.
                app.switch_page("views/product_detail.py").run()
                app.button(key="run_review_baseline").click().run()
                self.assertEqual(len(app.exception), 0)
                with connect(database) as connection:
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM agent_logs").fetchone()[0], 2)
                app.run()
                with connect(database) as connection:
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM agent_logs").fetchone()[0], 2)
                submit = next(button for button in app.button if "구매적합도 분석" in button.label)
                submit.click().run()
                self.assertEqual(len(app.exception), 0)
                app.switch_page("views/fit_result.py").run()
                self.assertEqual(len(app.exception), 0)
                self.assertIsNotNone(app.session_state["fit_result"]["result"]["score"])
                app.switch_page("views/admin_dashboard.py").run()
                self.assertEqual(len(app.exception), 0)
                with connect(database) as connection:
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM agent_logs").fetchone()[0], 4)
                    before = connection.execute("SELECT COUNT(*) FROM resource_logs").fetchone()[0]
                app.button(key="refresh_dashboard").click().run()
                self.assertEqual(len(app.exception), 0)
                with connect(database) as connection:
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM resource_logs").fetchone()[0], before)


if __name__ == "__main__":
    unittest.main()
