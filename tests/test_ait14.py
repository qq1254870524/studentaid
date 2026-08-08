from __future__ import annotations

import csv
import sqlite3
import sys
import tempfile
from pathlib import Path
import threading
import unittest

sys.dont_write_bytecode = True
module_root = Path(__file__).resolve().parent
if not (module_root / "ait14.py").is_file():
    module_root = module_root.parent
sys.path.insert(0, str(module_root))

import ait14 as ait11


def make_record(row: int, ssn: str) -> ait11.ImportedRecord:
    details = ait11.AccountDetails(
        first_name="FIRST",
        last_name="LAST",
        birth_month="01",
        birth_day="02",
        birth_year="1963",
        ssn=ssn,
        original_ssn=ssn,
    )
    return ait11.ImportedRecord(
        source_file="input.xlsx",
        source_sheet="Sheet1",
        source_row=row,
        original_fields=(ssn, "01", "02", "1963", "LAST", "FIRST", "ADDRESS"),
        details=details,
        address="ADDRESS",
    )


class Step16DuplicateQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        ait11.DatabaseWriter._create_schema(self.connection)
        ait11.DatabaseWriter._handle(
            self.connection,
            "create_batch",
            {
                "batch_id": "batch",
                "input_path": "input.xlsx",
                "output_directory": ".",
                "thread_count": 8,
            },
        )

    def tearDown(self) -> None:
        self.connection.close()

    def test_only_one_work_item_per_normalised_first_column(self) -> None:
        records = [
            make_record(1, "111223333"),
            make_record(2, "111223333"),
            make_record(3, "111223333"),
            make_record(4, "444556666"),
            ait11.ImportedRecord(
                source_file="input.xlsx",
                source_sheet="Sheet1",
                source_row=5,
                original_fields=("bad",),
                details=None,
                address="",
                import_error="Social Security Number 必须包含 9 位数字",
            ),
        ]
        work_items = ait11.DatabaseWriter._handle(
            self.connection,
            "insert_records",
            {"batch_id": "batch", "records": records},
        )

        self.assertEqual(2, len(work_items))
        self.assertEqual(["111223333", "444556666"], [x.details.ssn for x in work_items])
        counts = dict(
            self.connection.execute(
                "SELECT status, COUNT(*) FROM records GROUP BY status"
            ).fetchall()
        )
        self.assertEqual({"failed": 1, "pending": 4}, counts)

    def test_group_completion_and_failure_cover_all_duplicates(self) -> None:
        records = [
            make_record(1, "111223333"),
            make_record(2, "111223333"),
            make_record(3, "111223333"),
        ]
        work_items = ait11.DatabaseWriter._handle(
            self.connection,
            "insert_records",
            {"batch_id": "batch", "records": records},
        )
        ait11.DatabaseWriter._handle(
            self.connection,
            "mark_processing",
            {"record_id": work_items[0].record_id},
        )
        result = ait11.RecoveryResult(
            result_code="account_not_found",
            heading="Account Not Found",
            masked_phone="",
            masked_email="",
            recovery_method="",
        )
        completed = ait11.DatabaseWriter._handle(
            self.connection,
            "mark_completed_group",
            {
                "batch_id": "batch",
                "ssn": "111223333",
                "result": result,
            },
        )
        self.assertEqual(3, completed)
        self.assertEqual(
            [("completed", 3)],
            [
                tuple(row)
                for row in self.connection.execute(
                    "SELECT status, COUNT(*) FROM records GROUP BY status"
                ).fetchall()
            ],
        )

        failed = ait11.DatabaseWriter._handle(
            self.connection,
            "mark_failed_group",
            {
                "batch_id": "batch",
                "ssn": "111223333",
                "error": "output write failed",
            },
        )
        self.assertEqual(3, failed)
        self.assertEqual(
            [("failed", 3)],
            [
                tuple(row)
                for row in self.connection.execute(
                    "SELECT status, COUNT(*) FROM records GROUP BY status"
                ).fetchall()
            ],
        )

    def test_retry_returns_the_whole_duplicate_group_to_pending(self) -> None:
        records = [
            make_record(1, "111223333"),
            make_record(2, "111223333"),
            make_record(3, "111223333"),
        ]
        work_items = ait11.DatabaseWriter._handle(
            self.connection,
            "insert_records",
            {"batch_id": "batch", "records": records},
        )
        ait11.DatabaseWriter._handle(
            self.connection,
            "mark_processing",
            {"record_id": work_items[0].record_id},
        )

        retried = ait11.DatabaseWriter._handle(
            self.connection,
            "mark_retry_group",
            {
                "batch_id": "batch",
                "ssn": "111223333",
                "error": "temporary page timeout",
            },
        )

        self.assertEqual(3, retried)
        self.assertEqual(
            [("pending", 3)],
            [
                tuple(row)
                for row in self.connection.execute(
                    "SELECT status, COUNT(*) FROM records GROUP BY status"
                ).fetchall()
            ],
        )
        representative = self.connection.execute(
            "SELECT attempt_count, started_at, finished_at, error "
            "FROM records WHERE id=?",
            (work_items[0].record_id,),
        ).fetchone()
        self.assertEqual(1, representative["attempt_count"])
        self.assertIsNone(representative["started_at"])
        self.assertIsNone(representative["finished_at"])
        self.assertEqual("temporary page timeout", representative["error"])


class Step16CumulativeCsvTests(unittest.TestCase):
    def test_quote_all_normalisation_also_removes_empty_rows(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            output = Path(directory) / "result.csv"
            output.write_text(
                '\n"key","01/02/1963","FIRST","LAST","ADDRESS",'
                '"Account Not Found","","",""\n\n',
                encoding="utf-8-sig",
            )

            self.assertTrue(ait11.ensure_cumulative_output_quote_all(output))
            text = output.read_text(encoding="utf-8-sig")
            rows = list(csv.reader(text.splitlines()))
            self.assertEqual(1, len(rows))
            self.assertEqual(9, len(rows[0]))
            self.assertTrue(text.startswith('"key","01/02/1963"'))
            self.assertFalse(ait11.ensure_cumulative_output_quote_all(output))


class FakeSession:
    processed: list[str] = []
    lock = threading.Lock()

    def __init__(self, worker_number: int) -> None:
        self.worker_number = worker_number

    def start(self) -> None:
        return None

    def process(self, item, stop_event, progress):
        with self.lock:
            self.processed.append(item.details.ssn)
        return ait11.RecoveryResult(
            result_code="account_not_found",
            heading="Account Not Found",
            masked_phone="",
            masked_email="",
            recovery_method="",
        )

    def prepare_for_next(self, result_code, stop_event, progress) -> None:
        return None

    def recover_after_cleanup_error(self) -> None:
        return None

    def close(self) -> None:
        return None


class FlakySession(FakeSession):
    attempts: dict[str, int] = {}
    sequence: list[str] = []

    def process(self, item, stop_event, progress):
        with self.lock:
            attempts = self.attempts.get(item.details.ssn, 0) + 1
            self.attempts[item.details.ssn] = attempts
            self.sequence.append(item.details.ssn)
        if item.details.ssn == "111223333" and attempts == 1:
            raise RuntimeError("temporary page timeout")
        return ait11.RecoveryResult(
            result_code="account_not_found",
            heading="Account Not Found",
            masked_phone="",
            masked_email="",
            recovery_method="",
        )


class AlwaysFailSession(FakeSession):
    calls = 0

    def process(self, item, stop_event, progress):
        with self.lock:
            type(self).calls += 1
        raise RuntimeError("persistent page timeout")


class Step16BatchIntegrationTests(unittest.TestCase):
    def test_duplicate_rows_use_one_browser_task_and_finish_as_group(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "output.csv"
            rows = [
                ["111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS"],
                ["111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS"],
                ["111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS"],
                ["444556666", "01", "02", "1963", "LAST", "FIRST", "ADDRESS"],
                ["444556666", "01", "02", "1963", "LAST", "FIRST", "ADDRESS"],
            ]
            with input_path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerows(rows)
            output_path.write_text("\n", encoding="utf-8-sig")

            events: list[tuple[str, dict]] = []
            FakeSession.processed = []
            engine = ait11.BatchEngine(
                lambda kind, payload: events.append((kind, payload)),
                session_factory=FakeSession,
            )
            engine.start(
                input_path,
                output_path,
                thread_count=12,
                backend="playwright",
                display_mode="窗口",
            )
            self.assertTrue(engine.wait(10))
            self.assertFalse(any(kind == "fatal" for kind, _ in events))
            self.assertEqual(
                ["111223333", "444556666"],
                sorted(FakeSession.processed),
            )
            self.assertEqual("", input_path.read_text(encoding="utf-8-sig"))

            output_rows = list(
                csv.reader(output_path.read_text(encoding="utf-8-sig").splitlines())
            )
            self.assertEqual(2, len(output_rows))
            self.assertTrue(all(len(row) == 9 for row in output_rows))

            connection = sqlite3.connect(root / ait11.DATABASE_FILENAME)
            try:
                status_counts = dict(
                    connection.execute(
                        "SELECT status, COUNT(*) FROM records GROUP BY status"
                    ).fetchall()
                )
            finally:
                connection.close()
            self.assertEqual({"completed": 5}, status_counts)
            connection = sqlite3.connect(root / ait11.DATABASE_FILENAME)
            try:
                configured_threads = connection.execute(
                    "SELECT thread_count FROM batches ORDER BY created_at DESC LIMIT 1"
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(12, configured_threads)
            log_text = "\n".join(
                payload.get("message", "") for kind, payload in events if kind == "log"
            )
            self.assertIn("唯一浏览器任务 2 个", log_text)
            self.assertIn("同第一列重复 3 条", log_text)

    def test_transient_failure_is_retried_from_queue_tail(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "output.csv"
            rows = [
                ["111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS"],
                ["111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS"],
                ["444556666", "01", "02", "1963", "LAST", "FIRST", "ADDRESS"],
            ]
            with input_path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerows(rows)

            events: list[tuple[str, dict]] = []
            FlakySession.attempts = {}
            FlakySession.sequence = []
            engine = ait11.BatchEngine(
                lambda kind, payload: events.append((kind, payload)),
                session_factory=FlakySession,
            )
            engine.start(
                input_path,
                output_path,
                thread_count=1,
                backend="playwright",
                display_mode="窗口",
            )
            self.assertTrue(engine.wait(10))
            self.assertFalse(any(kind == "fatal" for kind, _ in events))
            self.assertEqual(
                {"111223333": 2, "444556666": 1}, FlakySession.attempts
            )
            self.assertEqual(
                ["111223333", "444556666", "111223333"],
                FlakySession.sequence,
            )
            self.assertEqual("", input_path.read_text(encoding="utf-8-sig"))
            output_rows = list(
                csv.reader(output_path.read_text(encoding="utf-8-sig").splitlines())
            )
            self.assertEqual(2, len(output_rows))
            self.assertTrue(all(len(row) == 9 for row in output_rows))

            connection = sqlite3.connect(root / ait11.DATABASE_FILENAME)
            try:
                status_counts = dict(
                    connection.execute(
                        "SELECT status, COUNT(*) FROM records GROUP BY status"
                    ).fetchall()
                )
                max_attempts = connection.execute(
                    "SELECT MAX(attempt_count) FROM records"
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual({"completed": 3}, status_counts)
            self.assertEqual(2, max_attempts)
            log_text = "\n".join(
                payload.get("message", "") for kind, payload in events if kind == "log"
            )
            self.assertIn("已回到队尾", log_text)
            self.assertIn("第 2/3 轮", log_text)

    def test_persistent_failure_stops_after_three_queue_rounds(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "output.csv"
            with input_path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerow(
                    ["111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS"]
                )

            events: list[tuple[str, dict]] = []
            AlwaysFailSession.calls = 0
            engine = ait11.BatchEngine(
                lambda kind, payload: events.append((kind, payload)),
                session_factory=AlwaysFailSession,
            )
            engine.start(
                input_path,
                output_path,
                thread_count=1,
                backend="playwright",
                display_mode="窗口",
            )
            self.assertTrue(engine.wait(10))
            self.assertFalse(any(kind == "fatal" for kind, _ in events))
            self.assertEqual(ait11.MAX_QUEUE_ATTEMPTS, AlwaysFailSession.calls)
            self.assertTrue(input_path.read_text(encoding="utf-8-sig").strip())
            self.assertFalse(output_path.exists())

            connection = sqlite3.connect(root / ait11.DATABASE_FILENAME)
            try:
                status, attempts, error = connection.execute(
                    "SELECT status, attempt_count, error FROM records"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual("failed", status)
            self.assertEqual(ait11.MAX_QUEUE_ATTEMPTS, attempts)
            self.assertEqual("persistent page timeout", error)


class _TextLocator:
    def __init__(self, text: str, visible: bool = True) -> None:
        self._text = text
        self._visible = visible

    @property
    def first(self):
        return self

    def is_visible(self) -> bool:
        return self._visible

    def inner_text(self) -> str:
        return self._text


class _ResultPage:
    def __init__(self, body_text: str) -> None:
        self.body_text = body_text

    def evaluate(self, _script: str) -> str:
        return self.body_text

    def wait_for_timeout(self, _milliseconds: int) -> None:
        return None

    def get_by_text(self, text, exact=False):
        if isinstance(text, str) and text in self.body_text:
            return _TextLocator(text)
        return _TextLocator("", visible=False)


class Step18ExplicitStatusTests(unittest.TestCase):
    def test_account_lookup_issue_is_an_explicit_result(self) -> None:
        page = _ResultPage(ait11.ACCOUNT_LOOKUP_ISSUE_HEADING)
        status = ait11.step_4_judge_password_recovery(
            page,
            threading.Event(),
            timeout_ms=100,
        )
        self.assertEqual("account_lookup_issue", status)
        result = ait11.collect_recovery_result(page, status)
        self.assertEqual(ait11.ACCOUNT_LOOKUP_ISSUE_HEADING, result.heading)
        self.assertEqual(("", "", ""), (
            result.masked_phone,
            result.masked_email,
            result.recovery_method,
        ))

    def test_photo_id_recovery_message_is_an_explicit_result(self) -> None:
        page = _ResultPage(
            ait11.PHOTO_ID_RECOVERY_MESSAGE.replace(
                "information. Access", "information.\n   Access"
            )
        )
        status = ait11.step_4_judge_password_recovery(
            page,
            threading.Event(),
            timeout_ms=100,
        )
        self.assertEqual("photo_id_recovery_required", status)
        result = ait11.collect_recovery_result(page, status)
        self.assertEqual(ait11.PHOTO_ID_RECOVERY_MESSAGE, result.heading)
        self.assertEqual(("", "", ""), (
            result.masked_phone,
            result.masked_email,
            result.recovery_method,
        ))

    def test_new_statuses_use_existing_terminal_cleanup_path(self) -> None:
        session = ait11.BrowserRecoverySession.__new__(ait11.BrowserRecoverySession)
        calls: list[str] = []
        session._page = None
        session._clear_browser_data_and_blank = lambda progress: calls.append("clear")
        session._close_page = lambda: calls.append("close")
        for status in (
            "account_lookup_issue",
            "photo_id_recovery_required",
            "invalid_ssn",
        ):
            session.prepare_for_next(status, threading.Event())
        self.assertEqual(["clear", "clear", "clear"], calls)

    def test_zero_threads_is_rejected_but_no_upper_limit_is_applied(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            input_path.write_text(
                "111223333,01,02,1963,LAST,FIRST,ADDRESS\n",
                encoding="utf-8-sig",
            )
            engine = ait11.BatchEngine(lambda *_: None, session_factory=FakeSession)
            with self.assertRaisesRegex(ValueError, "大于等于 1"):
                engine.start(
                    input_path,
                    root / "output.csv",
                    thread_count=0,
                    backend="playwright",
                    display_mode="窗口",
                )


class Step19DynamicColumnsAndSsnValidationTests(unittest.TestCase):
    def test_invalid_ssn_page_message_is_an_explicit_result(self) -> None:
        page = _ResultPage(ait11.INVALID_SSN_MESSAGE)
        status = ait11.step_4_judge_password_recovery(
            page,
            threading.Event(),
            timeout_ms=100,
        )
        self.assertEqual("invalid_ssn", status)
        result = ait11.collect_recovery_result(page, status)
        self.assertEqual(ait11.INVALID_SSN_MESSAGE, result.heading)
        self.assertEqual(("", "", ""), (
            result.masked_phone,
            result.masked_email,
            result.recovery_method,
        ))

    def test_columns_after_first_four_are_preserved_separately(self) -> None:
        fields = (
            "111223333",
            "06/29/1963",
            "FIRST",
            "LAST",
            "ADDRESS",
            "EMAIL",
            "PHONE",
        )
        details, address = ait11._parse_input_row(fields, None)
        item = ait11.WorkItem(
            record_id=1,
            details=details,
            original_fields=fields,
            address=address,
        )
        result = ait11.RecoveryResult(
            result_code="invalid_ssn",
            heading=ait11.INVALID_SSN_MESSAGE,
            masked_phone="",
            masked_email="",
            recovery_method="",
        )
        row = ait11.build_cumulative_output_row(item, result)
        self.assertEqual(list(fields), row[:7])
        self.assertEqual(
            [ait11.INVALID_SSN_MESSAGE, "", "", ""],
            row[7:],
        )
        self.assertEqual(11, len(row))

    def test_four_column_input_needs_no_placeholder_column(self) -> None:
        fields = ("111223333", "1/2/1963", "FIRST", "LAST")
        details, address = ait11._parse_input_row(fields, None)
        item = ait11.WorkItem(
            record_id=1,
            details=details,
            original_fields=fields,
            address=address,
        )
        result = ait11.RecoveryResult("invalid_ssn", ait11.INVALID_SSN_MESSAGE, "", "", "")
        row = ait11.build_cumulative_output_row(item, result)
        self.assertEqual("01/02/1963", row[1])
        self.assertEqual(8, len(row))

    def test_legacy_split_date_row_keeps_existing_nine_columns(self) -> None:
        fields = ("111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS")
        details, address = ait11._parse_input_row(fields, None)
        item = ait11.WorkItem(
            record_id=1,
            details=details,
            original_fields=fields,
            address=address,
        )
        result = ait11.RecoveryResult("invalid_ssn", ait11.INVALID_SSN_MESSAGE, "", "", "")
        row = ait11.build_cumulative_output_row(item, result)
        self.assertEqual(
            ["111223333", "01/02/1963", "FIRST", "LAST", "ADDRESS"],
            row[:5],
        )
        self.assertEqual(9, len(row))

    def test_arbitrary_header_order_keeps_existing_canonical_output(self) -> None:
        details = ait11.AccountDetails(
            first_name="FIRST",
            last_name="LAST",
            birth_month="01",
            birth_day="02",
            birth_year="1963",
            ssn="111223333",
            original_ssn="111223333",
        )
        item = ait11.WorkItem(
            record_id=1,
            details=details,
            original_fields=("FIRST", "111223333", "01/02/1963", "LAST", "ADDRESS"),
            address="ADDRESS",
        )
        result = ait11.RecoveryResult("invalid_ssn", ait11.INVALID_SSN_MESSAGE, "", "", "")
        row = ait11.build_cumulative_output_row(item, result)
        self.assertEqual(
            ["FIRST", "01/02/1963", "FIRST", "LAST", "ADDRESS"],
            row[:5],
        )
        self.assertEqual(9, len(row))


if __name__ == "__main__":
    unittest.main(verbosity=2)
