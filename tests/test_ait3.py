import csv
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ait3


class SuccessSession:
    def __init__(self, worker_number: int) -> None:
        self.worker_number = worker_number
        self.browser_mode = "mock-success"

    def start(self) -> None:
        pass

    def process(self, item, stop_event):
        return ait3.RecoveryResult(
            result_code="account_not_found",
            heading="Account Not Found",
            masked_phone="",
            masked_email="",
            recovery_method="",
        )

    def close(self) -> None:
        pass


class FailureSession(SuccessSession):
    def process(self, item, stop_event):
        raise RuntimeError("simulated site failure")


class StudentAidStep8Tests(unittest.TestCase):
    def _input_file(self, root: Path) -> Path:
        path = root / "input.csv"
        path.write_text(
            '000000000,01,01,1990,Example,Test,"1 Test Road"\n',
            encoding="utf-8",
        )
        return path

    def _run_engine(self, session_factory):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        events = []
        engine = ait3.BatchEngine(
            event_callback=lambda kind, payload: events.append((kind, payload)),
            session_factory=session_factory,
        )
        engine.start(self._input_file(root), root / "output", 1)
        self.assertTrue(engine.wait(15), "engine did not finish")
        finished = [payload for kind, payload in events if kind == "finished"]
        self.assertEqual(len(finished), 1)
        return root, finished[0]

    def test_success_batch_exports_completed_row_and_valid_database(self):
        root, finished = self._run_engine(SuccessSession)
        self.assertEqual(finished["counts"]["completed"], 1)
        export_path = Path(finished["export_path"])
        with export_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Processing_Status"], "completed")
        self.assertEqual(rows[0]["Result_Heading"], "Account Not Found")

    def test_failed_batch_is_not_reported_as_completed_record(self):
        root, finished = self._run_engine(FailureSession)
        self.assertEqual(finished["counts"]["completed"], 0)
        self.assertEqual(finished["counts"]["failed"], 1)
        export_path = Path(finished["export_path"])
        with export_path.open("r", encoding="utf-8-sig", newline="") as handle:
            row = next(csv.DictReader(handle))
        self.assertEqual(row["Processing_Status"], "failed")
        self.assertIn("simulated site failure", row["Error"])

    def test_cdp_url_can_be_disabled_or_explicitly_selected(self):
        old = os.environ.get("STUDENTAID_CDP_URL")
        try:
            os.environ["STUDENTAID_CDP_URL"] = "off"
            self.assertEqual(ait3._candidate_cdp_urls(), [])
            os.environ["STUDENTAID_CDP_URL"] = "http://127.0.0.1:9333/"
            self.assertEqual(
                ait3._candidate_cdp_urls(), ["http://127.0.0.1:9333"]
            )
        finally:
            if old is None:
                os.environ.pop("STUDENTAID_CDP_URL", None)
            else:
                os.environ["STUDENTAID_CDP_URL"] = old

    @unittest.skipIf(ait3.sync_playwright is None, "playwright not installed")
    def test_submission_unknown_error_is_not_false_success(self):
        with ait3.sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.set_content(
                    '<h1>Retrieve Your Log-in Information</h1>'
                    '<input id="fsa_Input_ForgotUsernameFirstName">'
                    '<div id="status">Loading...</div>'
                    '<script>setTimeout(() => {'
                    'document.getElementById("status").textContent = '
                    '"An unknown error has occurred. Please try again later";'
                    '}, 50);</script>'
                )
                with self.assertRaisesRegex(RuntimeError, "未知错误"):
                    ait3.step_4_judge_password_recovery(page, threading.Event())
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
