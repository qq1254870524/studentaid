from __future__ import annotations

import csv
import sqlite3
import sys
import tempfile
from pathlib import Path
import threading
import time
import unittest

sys.dont_write_bytecode = True
module_root = Path(__file__).resolve().parent
if not (module_root / "ait22.py").is_file():
    module_root = module_root.parent
sys.path.insert(0, str(module_root))

import ait22 as ait11


class GuiConfigPersistenceTests(unittest.TestCase):
    def test_save_and_load_restores_all_gui_values(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            config_path = Path(directory) / ait11.GUI_CONFIG_FILENAME
            expected = {
                "input_path": r"E:\studentaid\假资料测试2.xlsx",
                "output_path": r"E:\studentaid\StudentAid累计结果.csv",
                "backend": "playwright",
                "display_mode": "窗口",
                "thread_count": "12",
            }
            ait11.save_gui_config(expected, config_path)
            self.assertEqual(expected, ait11.load_gui_config(config_path))
            self.assertTrue(config_path.is_file())

    def test_invalid_or_corrupt_config_falls_back_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            config_path = Path(directory) / ait11.GUI_CONFIG_FILENAME
            config_path.write_text("{not-json", encoding="utf-8")
            loaded = ait11.load_gui_config(config_path)
            self.assertEqual("browser-use", loaded["backend"])
            self.assertEqual("无头", loaded["display_mode"])
            self.assertEqual("2", loaded["thread_count"])

            ait11.save_gui_config(
                {
                    "backend": "unknown",
                    "display_mode": "bad",
                    "thread_count": "0",
                },
                config_path,
            )
            loaded = ait11.load_gui_config(config_path)
            self.assertEqual("browser-use", loaded["backend"])
            self.assertEqual("无头", loaded["display_mode"])
            self.assertEqual("2", loaded["thread_count"])


class Step24RealtimeProgressMetricsTests(unittest.TestCase):
    def test_percentage_rolling_minute_rate_average_and_eta(self) -> None:
        tracker = ait11.BatchProgressTracker()
        tracker.start(now=100.0)
        baseline = tracker.update(
            {
                "total": 100,
                "pending": 100,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "stopped": 0,
            },
            now=100.0,
        )
        self.assertEqual(0, baseline.recent_minute_count)
        self.assertIsNone(baseline.eta_seconds)

        metrics = tracker.update(
            {
                "total": 100,
                "pending": 75,
                "processing": 5,
                "completed": 18,
                "failed": 2,
                "stopped": 0,
            },
            now=130.0,
        )
        self.assertEqual(20, metrics.terminal)
        self.assertEqual(80, metrics.remaining)
        self.assertEqual(20.0, metrics.percent)
        self.assertEqual(20, metrics.recent_minute_count)
        self.assertAlmostEqual(40.0, metrics.average_per_minute)
        self.assertAlmostEqual(120.0, metrics.eta_seconds or 0.0)

        after_window = tracker.snapshot(now=191.0)
        self.assertEqual(0, after_window.recent_minute_count)
        self.assertGreater(after_window.average_per_minute, 0)

    def test_initial_import_failures_are_not_counted_as_browser_speed(self) -> None:
        tracker = ait11.BatchProgressTracker()
        tracker.start(now=0.0)
        metrics = tracker.update(
            {
                "total": 10,
                "pending": 7,
                "processing": 0,
                "completed": 0,
                "failed": 3,
                "stopped": 0,
            },
            now=5.0,
        )
        self.assertEqual(30.0, metrics.percent)
        self.assertEqual(0, metrics.recent_minute_count)
        self.assertEqual(0.0, metrics.average_per_minute)
        self.assertIsNone(metrics.eta_seconds)

    def test_stale_event_does_not_move_processed_count_backwards(self) -> None:
        tracker = ait11.BatchProgressTracker()
        tracker.start(now=0.0)
        tracker.update(
            {"total": 10, "pending": 10, "processing": 0}, now=0.0
        )
        current = tracker.update(
            {"total": 10, "pending": 5, "processing": 1, "completed": 4},
            now=20.0,
        )
        stale = tracker.update(
            {"total": 10, "pending": 8, "processing": 1, "completed": 1},
            now=21.0,
        )
        self.assertEqual(current.terminal, stale.terminal)
        self.assertEqual(current.percent, stale.percent)

    def test_finish_freezes_elapsed_time_and_duration_format(self) -> None:
        tracker = ait11.BatchProgressTracker()
        tracker.start(now=10.0)
        tracker.update(
            {"total": 2, "pending": 2, "processing": 0}, now=10.0
        )
        tracker.update(
            {"total": 2, "pending": 0, "processing": 0, "completed": 2},
            now=70.0,
        )
        tracker.finish(now=80.0)
        frozen = tracker.snapshot(now=500.0)
        self.assertEqual(70.0, frozen.elapsed_seconds)
        self.assertEqual(0.0, frozen.eta_seconds)
        self.assertEqual("00:01:10", ait11.format_duration(frozen.elapsed_seconds))
        self.assertEqual("--", ait11.format_duration(None))
        self.assertEqual("1天 01:01:01", ait11.format_duration(90061))


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

    def test_same_ssn_with_different_full_rows_creates_separate_tasks(self) -> None:
        first = make_record(1, "111223333")
        second = ait11.ImportedRecord(
            source_file=first.source_file,
            source_sheet=first.source_sheet,
            source_row=2,
            original_fields=(
                "111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS 2",
            ),
            details=first.details,
            address="ADDRESS 2",
        )
        work_items = ait11.DatabaseWriter._handle(
            self.connection,
            "insert_records",
            {"batch_id": "batch", "records": [first, second]},
        )
        self.assertEqual(2, len(work_items))
        self.assertEqual("111223333", work_items[0].details.ssn)
        self.assertEqual("111223333", work_items[1].details.ssn)
        self.assertNotEqual(work_items[0].record_key, work_items[1].record_key)

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
                "record_key": work_items[0].record_key,
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
                "record_key": work_items[0].record_key,
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
                "record_key": work_items[0].record_key,
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


def make_work_item(record_id: int, ssn: str) -> ait11.WorkItem:
    record = make_record(record_id, ssn)
    assert record.details is not None
    return ait11.WorkItem(
        record_id=record_id,
        details=record.details,
        source_file=record.source_file,
        source_sheet=record.source_sheet,
        source_row=record.source_row,
        original_fields=record.original_fields,
        address=record.address,
    )


class Step23PersistencePipelineTests(unittest.TestCase):
    def test_same_ssn_different_rows_are_both_appended_and_deleted(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "output.csv"
            first = make_work_item(1, "111223333")
            second = ait11.WorkItem(
                record_id=2,
                details=first.details,
                source_file=first.source_file,
                source_sheet=first.source_sheet,
                source_row=2,
                original_fields=(
                    "111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS 2",
                ),
                address="ADDRESS 2",
            )
            with input_path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerows(
                    [first.original_fields, second.original_fields]
                )
            result = ait11.RecoveryResult(
                "account_not_found", "Account Not Found", "", "", ""
            )
            writer = ait11.ResultPersistenceWriter(
                input_path, output_path, batch_size=2, flush_seconds=60
            )
            writer.start()
            self.assertTrue(writer.commit(first, result))
            self.assertTrue(writer.commit(second, result))
            writer.close()
            rows = list(
                csv.reader(output_path.read_text(encoding="utf-8-sig").splitlines())
            )
            self.assertEqual(2, len(rows))
            self.assertEqual("ADDRESS", rows[0][6])
            self.assertEqual("ADDRESS 2", rows[1][6])
            self.assertEqual("", input_path.read_text(encoding="utf-8-sig"))

    def test_startup_sync_removes_only_exact_output_row(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "output.csv"
            first = make_work_item(1, "111223333")
            second_fields = (
                "111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS 2",
            )
            with input_path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerows([first.original_fields, second_fields])
            result = ait11.RecoveryResult(
                "account_not_found", "Account Not Found", "", "", ""
            )
            ait11.append_cumulative_result(output_path, first, result)
            keys = ait11.read_output_row_keys(output_path)
            self.assertEqual(1, len(keys))
            self.assertEqual(1, ait11.remove_input_rows_by_keys(input_path, keys))
            remaining = list(
                csv.reader(input_path.read_text(encoding="utf-8-sig").splitlines())
            )
            self.assertEqual([list(second_fields)], remaining)

    def test_batch_duplicate_cleanup_keeps_different_row_with_same_ssn(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "input.csv"
            rows = [
                ["111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS"],
                ["111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS"],
                ["111223333", "01", "02", "1963", "LAST", "FIRST", "ADDRESS 2"],
            ]
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerows(rows)
            records = ait11.load_input_records(path)
            self.assertEqual(1, ait11.remove_duplicate_input_rows(path))
            remaining = list(
                csv.reader(path.read_text(encoding="utf-8-sig").splitlines())
            )
            self.assertEqual([rows[0], rows[2]], remaining)

    def test_twenty_results_use_one_batched_input_rewrite(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "output.csv"
            items = [
                make_work_item(index, f"{100000000 + index:09d}")
                for index in range(1, 21)
            ]
            with input_path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerows(item.original_fields for item in items)
            result = ait11.RecoveryResult(
                result_code="account_not_found",
                heading="Account Not Found",
                masked_phone="",
                masked_email="",
                recovery_method="",
            )
            original_remove = ait11.remove_input_rows_by_keys
            delete_calls: list[set[str]] = []

            def tracked_remove(path, keys):
                delete_calls.append(set(keys))
                return original_remove(path, keys)

            ait11.remove_input_rows_by_keys = tracked_remove
            try:
                writer = ait11.ResultPersistenceWriter(
                    input_path,
                    output_path,
                    batch_size=20,
                    flush_seconds=60,
                )
                writer.start()
                self.assertTrue(all(writer.commit(item, result) for item in items))
                writer.close()
            finally:
                ait11.remove_input_rows_by_keys = original_remove

            self.assertEqual(1, len(delete_calls))
            self.assertEqual(20, len(delete_calls[0]))
            self.assertEqual("", input_path.read_text(encoding="utf-8-sig"))
            rows = list(
                csv.reader(output_path.read_text(encoding="utf-8-sig").splitlines())
            )
            self.assertEqual(20, len(rows))

    def test_browser_commit_does_not_wait_for_slow_input_rewrite(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "output.csv"
            item = make_work_item(1, "111223333")
            with input_path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerow(item.original_fields)
            result = ait11.RecoveryResult(
                result_code="account_not_found",
                heading="Account Not Found",
                masked_phone="",
                masked_email="",
                recovery_method="",
            )
            original_remove = ait11.remove_input_rows_by_keys
            delete_started = threading.Event()
            allow_delete = threading.Event()

            def slow_remove(path, keys):
                delete_started.set()
                self.assertTrue(allow_delete.wait(3))
                return original_remove(path, keys)

            ait11.remove_input_rows_by_keys = slow_remove
            try:
                writer = ait11.ResultPersistenceWriter(
                    input_path,
                    output_path,
                    batch_size=1,
                    flush_seconds=60,
                )
                writer.start()
                started = time.perf_counter()
                self.assertTrue(writer.commit(item, result))
                elapsed = time.perf_counter() - started
                self.assertLess(elapsed, 0.5)
                self.assertTrue(delete_started.wait(1))
                allow_delete.set()
                writer.close()
            finally:
                allow_delete.set()
                ait11.remove_input_rows_by_keys = original_remove

            self.assertEqual("", input_path.read_text(encoding="utf-8-sig"))

    def test_duplicate_output_key_is_not_appended_twice_but_input_is_deleted(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "output.csv"
            item = make_work_item(1, "111223333")
            with input_path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerow(item.original_fields)
            result = ait11.RecoveryResult(
                result_code="account_not_found",
                heading="Account Not Found",
                masked_phone="",
                masked_email="",
                recovery_method="",
            )
            writer = ait11.ResultPersistenceWriter(
                input_path,
                output_path,
                batch_size=20,
                flush_seconds=60,
            )
            writer.start()
            self.assertTrue(writer.commit(item, result))
            self.assertFalse(writer.commit(item, result))
            writer.close()
            rows = list(
                csv.reader(output_path.read_text(encoding="utf-8-sig").splitlines())
            )
            self.assertEqual(1, len(rows))
            self.assertEqual("", input_path.read_text(encoding="utf-8-sig"))

    def test_time_threshold_flushes_a_small_batch(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "output.csv"
            item = make_work_item(1, "111223333")
            with input_path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerow(item.original_fields)
            result = ait11.RecoveryResult(
                "account_not_found", "Account Not Found", "", "", ""
            )
            writer = ait11.ResultPersistenceWriter(
                input_path,
                output_path,
                batch_size=20,
                flush_seconds=0.1,
            )
            writer.start()
            self.assertTrue(writer.commit(item, result))
            deadline = time.monotonic() + 2
            while input_path.read_text(encoding="utf-8-sig") and time.monotonic() < deadline:
                time.sleep(0.02)
            writer.close()
            self.assertEqual("", input_path.read_text(encoding="utf-8-sig"))

    def test_output_remains_recoverable_when_input_rewrite_fails(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "output.csv"
            item = make_work_item(1, "111223333")
            with input_path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerow(item.original_fields)
            result = ait11.RecoveryResult(
                "account_not_found", "Account Not Found", "", "", ""
            )
            original_remove = ait11.remove_input_rows_by_keys

            def failed_remove(_path, _keys):
                raise PermissionError("input file is busy")

            ait11.remove_input_rows_by_keys = failed_remove
            try:
                writer = ait11.ResultPersistenceWriter(
                    input_path,
                    output_path,
                    batch_size=1,
                    flush_seconds=60,
                )
                writer.start()
                self.assertTrue(writer.commit(item, result))
                with self.assertRaisesRegex(RuntimeError, "等待下次启动同步删除"):
                    writer.close()
            finally:
                ait11.remove_input_rows_by_keys = original_remove

            output_keys = ait11.read_output_first_column_keys(output_path)
            self.assertIn(item.record_key, output_keys)
            self.assertTrue(input_path.read_text(encoding="utf-8-sig").strip())
            self.assertEqual(
                1,
                ait11.remove_input_rows_by_keys(input_path, output_keys),
            )
            self.assertEqual("", input_path.read_text(encoding="utf-8-sig"))


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
            self.assertTrue(all(len(row) == 11 for row in output_rows))

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
            self.assertIn("完全重复整行 3 条", log_text)

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
            self.assertTrue(all(len(row) == 11 for row in output_rows))

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
        self.assertEqual(list(fields), row[:-4])
        self.assertEqual("1/2/1963", row[1])
        self.assertEqual(8, len(row))

    def test_legacy_split_date_row_preserves_all_seven_input_columns(self) -> None:
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
        self.assertEqual(list(fields), row[:-4])
        self.assertEqual(11, len(row))

    def test_arbitrary_header_order_is_preserved_exactly(self) -> None:
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
        self.assertEqual(list(item.original_fields), row[:-4])
        self.assertEqual(9, len(row))


class Step25MyLifeFormatAdaptationTests(unittest.TestCase):
    header = (
        "primary_phone", "ssn", "known_birthday", "full_name", "age",
        "current_address", "city", "state", "zip_code", "email", "phone",
        "birth_year", "reference_age", "column_14", "column_15", "column_16",
        "生日", "性别", "星座", "备注原因",
    )

    def make_row(
        self,
        ssn: str = "487-78-6185",
        known_birthday: str = "1972-09-06",
        full_name: str = "Mary Dangerfield",
        final_birthday: str = "09/07/1972",
    ) -> tuple[str, ...]:
        return (
            "2817334560", ssn, known_birthday, full_name, "53",
            "1515 Rudel Dr #1108", "Tomball", "TX", "77375",
            "person@example.com", "(936) 253-4235", "1972", "53",
            "", "", "", final_birthday, "Female", "Virgo", "matched",
        )

    def test_header_maps_ssn_full_name_preferred_dob_and_address(self) -> None:
        mapping = ait11._header_mapping(self.header)
        self.assertIsNotNone(mapping)
        assert mapping is not None
        self.assertEqual(1, mapping["ssn"])
        self.assertEqual(2, mapping["dob"])
        self.assertEqual(3, mapping["full_name"])
        self.assertEqual(5, mapping["address"])
        self.assertEqual(16, mapping["preferred_dob"])

        details, address = ait11._parse_input_row(self.make_row(), mapping)
        self.assertEqual("487786185", details.ssn)
        self.assertEqual(("Mary", "Dangerfield"), (details.first_name, details.last_name))
        self.assertEqual(("09", "07", "1972"), (
            details.birth_month, details.birth_day, details.birth_year,
        ))
        self.assertEqual("1515 Rudel Dr #1108", address)

    def test_empty_preferred_dob_falls_back_to_known_birthday(self) -> None:
        mapping = ait11._header_mapping(self.header)
        assert mapping is not None
        details, _address = ait11._parse_input_row(
            self.make_row(final_birthday=""), mapping
        )
        self.assertEqual(("09", "06", "1972"), (
            details.birth_month, details.birth_day, details.birth_year,
        ))

    def test_output_preserves_every_original_column_then_appends_results(self) -> None:
        mapping = ait11._header_mapping(self.header)
        assert mapping is not None
        fields = self.make_row()
        details, address = ait11._parse_input_row(fields, mapping)
        item = ait11.WorkItem(
            record_id=1,
            details=details,
            original_fields=fields,
            address=address,
            input_mapping=ait11._freeze_mapping(mapping),
        )
        result = ait11.RecoveryResult(
            "account_not_found", "Account Not Found", "", "", "",
        )
        output = ait11.build_cumulative_output_row(item, result)
        self.assertEqual(item.record_key, ait11._input_row_key(details, fields, address, ait11._freeze_mapping(mapping)))
        self.assertEqual(list(fields), output[:-4])
        self.assertEqual(24, len(output))
        self.assertEqual(["Account Not Found", "", "", ""], output[-4:])

    def test_mylife_same_ssn_but_any_later_column_change_has_different_key(self) -> None:
        mapping = ait11._header_mapping(self.header)
        assert mapping is not None
        first_fields = self.make_row()
        second_values = list(first_fields)
        second_values[-1] = "different note"
        second_fields = tuple(second_values)
        first_details, first_address = ait11._parse_input_row(first_fields, mapping)
        second_details, second_address = ait11._parse_input_row(second_fields, mapping)
        frozen_mapping = ait11._freeze_mapping(mapping)
        self.assertNotEqual(
            ait11._input_row_key(
                first_details, first_fields, first_address, frozen_mapping
            ),
            ait11._input_row_key(
                second_details, second_fields, second_address, frozen_mapping
            ),
        )
        case_values = list(first_fields)
        case_values[-1] = "MATCHED"
        case_fields = tuple(case_values)
        case_details, case_address = ait11._parse_input_row(case_fields, mapping)
        self.assertNotEqual(
            ait11._input_row_key(
                first_details, first_fields, first_address, frozen_mapping
            ),
            ait11._input_row_key(
                case_details, case_fields, case_address, frozen_mapping
            ),
        )

    def test_delete_by_output_ssn_uses_mapped_second_column(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "mylife.csv"
            rows = [
                self.header,
                self.make_row(ssn="487-78-6185"),
                self.make_row(ssn="589-70-1425", full_name="Robin Rochford"),
            ]
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerows(rows)
            record = ait11.load_input_records(path)[0]
            item = ait11.WorkItem(1, record.details, record.source_file, record.source_sheet, record.source_row, record.original_fields, record.address, record.input_mapping)
            removed = ait11.remove_input_rows_by_keys(path, {item.record_key})
            self.assertEqual(1, removed)
            remaining = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))
            self.assertEqual(2, len(remaining))
            self.assertEqual("ssn", remaining[0][1])
            self.assertEqual("589-70-1425", remaining[1][1])

    def test_mylife_format_imports_valid_and_missing_dob_rows(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "mylife.csv"
            rows = [
                self.header,
                self.make_row(ssn="487-78-6185"),
                self.make_row(
                    ssn="589-70-1425", full_name="Robin Rochford",
                    known_birthday="", final_birthday="",
                ),
            ]
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                csv.writer(stream).writerows(rows)
            records = ait11.load_input_records(path)
        valid = [record for record in records if not record.import_error]
        missing = [
            record for record in records
            if record.import_error.startswith("缺少必填字段：")
        ]
        self.assertEqual(2, len(records))
        self.assertEqual(1, len(valid))
        self.assertEqual(1, len(missing))
        self.assertTrue(all(dict(record.input_mapping).get("ssn") == 1 for record in records))


class Step20AccountRecoveryInProgressTests(unittest.TestCase):
    def test_account_recovery_in_progress_is_output_as_explicit_status(self) -> None:
        page = _ResultPage("Header\n  Account   Recovery In Progress  \nFooter")
        events: list[str] = []
        status = ait11.step_4_judge_password_recovery(
            page,
            threading.Event(),
            events.append,
            timeout_ms=100,
        )
        self.assertEqual("account_recovery_in_progress", status)
        result = ait11.collect_recovery_result(page, status)
        self.assertEqual(ait11.ACCOUNT_RECOVERY_IN_PROGRESS_HEADING, result.heading)
        self.assertEqual(("", "", ""), (
            result.masked_phone,
            result.masked_email,
            result.recovery_method,
        ))
        self.assertIn(
            f"已识别结果：{ait11.ACCOUNT_RECOVERY_IN_PROGRESS_HEADING}",
            events,
        )

    def test_account_recovery_in_progress_uses_terminal_cleanup(self) -> None:
        session = ait11.BrowserRecoverySession.__new__(ait11.BrowserRecoverySession)
        calls: list[str] = []
        session._page = None
        session._clear_browser_data_and_blank = lambda progress: calls.append("clear")
        session._close_page = lambda: calls.append("close")
        session.prepare_for_next(
            "account_recovery_in_progress",
            threading.Event(),
        )
        self.assertEqual(["clear"], calls)


class Step22AccountNotFoundStatusTests(unittest.TestCase):
    def test_create_new_account_heading_is_preserved_as_exact_result(self) -> None:
        page = _ResultPage(ait11.ACCOUNT_NOT_FOUND_CREATE_HEADING)
        events: list[str] = []
        status = ait11.step_4_judge_password_recovery(
            page,
            threading.Event(),
            events.append,
            timeout_ms=100,
        )
        self.assertEqual("account_not_found", status)
        result = ait11.collect_recovery_result(page, status)
        self.assertEqual(ait11.ACCOUNT_NOT_FOUND_CREATE_HEADING, result.heading)
        self.assertEqual(("", "", ""), (
            result.masked_phone,
            result.masked_email,
            result.recovery_method,
        ))
        self.assertIn(
            f"已识别结果：{ait11.ACCOUNT_NOT_FOUND_CREATE_HEADING}",
            events,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
