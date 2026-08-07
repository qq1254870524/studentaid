import csv
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ait4


class SuccessSession:
    def __init__(self, worker_number: int) -> None:
        self.worker_number = worker_number
        self.browser_mode = "mock-success"

    def start(self) -> None:
        pass

    def process(self, item, stop_event, progress_callback=None):
        if progress_callback is not None:
            progress_callback("mock stage reached")
        return ait4.RecoveryResult(
            result_code="account_not_found",
            heading="Account Not Found",
            masked_phone="",
            masked_email="",
            recovery_method="",
        )

    def close(self) -> None:
        pass


class FailureSession(SuccessSession):
    def process(self, item, stop_event, progress_callback=None):
        raise RuntimeError("simulated site failure")


class StudentAidStep9Tests(unittest.TestCase):
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
        engine = ait4.BatchEngine(
            event_callback=lambda kind, payload: events.append((kind, payload)),
            session_factory=session_factory,
        )
        engine.start(self._input_file(root), root / "output", 1)
        self.assertTrue(engine.wait(15), "engine did not finish")
        finished = [payload for kind, payload in events if kind == "finished"]
        self.assertEqual(len(finished), 1)
        return root, finished[0], events

    def test_success_batch_exports_completed_row_and_valid_database(self):
        root, finished, events = self._run_engine(SuccessSession)
        self.assertEqual(finished["counts"]["completed"], 1)
        export_path = Path(finished["export_path"])
        with export_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Processing_Status"], "completed")
        self.assertEqual(rows[0]["Result_Heading"], "Account Not Found")
        log_messages = [
            payload.get("message", "") for kind, payload in events if kind == "log"
        ]
        self.assertTrue(
            any("记录 #" in message and "mock stage reached" in message
                for message in log_messages),
            log_messages,
        )
        self.assertTrue(
            any("已实时写入 SQLite" in message for message in log_messages),
            log_messages,
        )

    def test_failed_batch_is_not_reported_as_completed_record(self):
        root, finished, events = self._run_engine(FailureSession)
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
            self.assertEqual(ait4._candidate_cdp_urls(), [])
            os.environ["STUDENTAID_CDP_URL"] = "http://127.0.0.1:9333/"
            self.assertEqual(
                ait4._candidate_cdp_urls(), ["http://127.0.0.1:9333"]
            )
        finally:
            if old is None:
                os.environ.pop("STUDENTAID_CDP_URL", None)
            else:
                os.environ["STUDENTAID_CDP_URL"] = old

    @unittest.skipIf(ait4.sync_playwright is None, "playwright not installed")
    def test_submission_unknown_error_is_not_false_success(self):
        with ait4.sync_playwright() as playwright:
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
                with self.assertRaisesRegex(ait4.PageSessionExpired, "会话已失效"):
                    ait4.step_4_judge_password_recovery(page, threading.Event())
            finally:
                browser.close()

    def test_cdp_session_reuses_default_context_without_closing_it(self):
        class FakePage:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        class ExistingContext:
            def __init__(self):
                self.pages = []
                self.closed = False

            def new_page(self):
                page = FakePage()
                self.pages.append(page)
                return page

            def close(self):
                self.closed = True

        class ExternalBrowser:
            def __init__(self):
                self.context = ExistingContext()
                self.contexts = [self.context]

            def new_context(self, **kwargs):
                raise AssertionError("CDP default context should be reused")

        session = ait4.BrowserRecoverySession(1)
        browser = ExternalBrowser()
        session._browser = browser
        session._external_browser = True
        item = ait4.WorkItem(
            record_id=1,
            details=ait4.AccountDetails(
                first_name="Test",
                last_name="Example",
                birth_month="01",
                birth_day="01",
                birth_year="1990",
                ssn="000000000",
                original_ssn="000000000",
            ),
        )
        expected = ait4.RecoveryResult(
            result_code="account_not_found",
            heading="Account Not Found",
            masked_phone="",
            masked_email="",
            recovery_method="",
        )
        with patch.object(ait4, "step_1_open_retrieve_account_details"), \
             patch.object(ait4, "step_2_fill_account_details"), \
             patch.object(ait4, "step_3_click_continue"), \
             patch.object(ait4, "step_4_judge_password_recovery", return_value="account_not_found"), \
             patch.object(ait4, "collect_recovery_result", return_value=expected):
            result = session.process(item, threading.Event())

        self.assertEqual(result, expected)
        self.assertEqual(len(browser.context.pages), 1)
        self.assertTrue(browser.context.pages[0].closed)
        self.assertFalse(browser.context.closed)

    def test_expired_page_is_reopened_and_refilled_once(self):
        class FakePage:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        class FakeContext:
            def __init__(self):
                self.pages = []
                self.closed = False

            def new_page(self):
                page = FakePage()
                self.pages.append(page)
                return page

            def close(self):
                self.closed = True

        class FakeBrowser:
            def __init__(self):
                self.context = FakeContext()

            def new_context(self, **kwargs):
                return self.context

        session = ait4.BrowserRecoverySession(1)
        browser = FakeBrowser()
        session._browser = browser
        details = ait4.AccountDetails(
            first_name="Test",
            last_name="Example",
            birth_month="01",
            birth_day="01",
            birth_year="1990",
            ssn="000000000",
            original_ssn="000000000",
        )
        item = ait4.WorkItem(record_id=1, details=details)
        messages = []
        statuses = [ait4.PageSessionExpired("expired"), "account_not_found"]
        expected = ait4.RecoveryResult(
            result_code="account_not_found",
            heading="Account Not Found",
            masked_phone="",
            masked_email="",
            recovery_method="",
        )

        def judge(*args, **kwargs):
            value = statuses.pop(0)
            if isinstance(value, BaseException):
                raise value
            return value

        with patch.object(ait4, "step_1_open_retrieve_account_details"), \
             patch.object(ait4, "step_2_fill_account_details"), \
             patch.object(ait4, "step_3_click_continue"), \
             patch.object(ait4, "step_4_judge_password_recovery", side_effect=judge), \
             patch.object(ait4, "collect_recovery_result", return_value=expected):
            result = session.process(item, threading.Event(), messages.append)

        self.assertEqual(result, expected)
        self.assertEqual(len(browser.context.pages), 2)
        self.assertTrue(all(page.closed for page in browser.context.pages))
        self.assertTrue(browser.context.closed)
        self.assertTrue(any("新开页面" in message for message in messages))

    @unittest.skipIf(ait4.sync_playwright is None, "playwright not installed")
    def test_form_disappearance_without_explicit_result_is_not_success(self):
        with ait4.sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.set_content(
                    '<input id="fsa_Input_ForgotUsernameFirstName">'
                    '<div id="status">Loading...</div>'
                    '<script>setTimeout(() => {'
                    'document.getElementById("status").textContent = "";'
                    'document.getElementById('
                    '"fsa_Input_ForgotUsernameFirstName").remove();'
                    '}, 40);</script>'
                )
                with self.assertRaisesRegex(RuntimeError, "明确结果超时"):
                    ait4.step_4_judge_password_recovery(
                        page,
                        threading.Event(),
                        timeout_ms=250,
                        poll_interval_ms=20,
                    )
            finally:
                browser.close()

    @unittest.skipIf(ait4.sync_playwright is None, "playwright not installed")
    def test_waiting_heartbeat_is_emitted_without_sensitive_values(self):
        messages = []
        with ait4.sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.set_content('<div>Loading...</div>')
                with self.assertRaisesRegex(RuntimeError, "明确结果超时"):
                    ait4.step_4_judge_password_recovery(
                        page,
                        threading.Event(),
                        messages.append,
                        timeout_ms=220,
                        poll_interval_ms=20,
                        heartbeat_seconds=0.05,
                    )
            finally:
                browser.close()
        self.assertTrue(any("仍在处理中" in message for message in messages))
        combined = " ".join(messages)
        self.assertNotIn("000000000", combined)
        self.assertNotIn("Example", combined)
        self.assertNotIn("Test Road", combined)

    @unittest.skipIf(ait4.sync_playwright is None, "playwright not installed")
    def test_explicit_photo_id_marker_is_success(self):
        with ait4.sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.set_content('<button>Recover my account with a photo ID</button>')
                status = ait4.step_4_judge_password_recovery(
                    page, threading.Event(), timeout_ms=500
                )
                self.assertEqual(status, "can_recover")
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
