import csv
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ait10


class StudentAidStep15InputCompatibilityTests(unittest.TestCase):
    def test_cumulative_csv_quote_all_keeps_dob_in_one_field(self):
        details = ait10.AccountDetails(
            first_name="First",
            last_name="Last",
            birth_month="01",
            birth_day="02",
            birth_year="1980",
            ssn="111223333",
            original_ssn="111-22-3333",
        )
        item = ait10.WorkItem(
            record_id=1,
            details=details,
            original_fields=("111-22-3333", "01/02/1980", "First", "Last"),
        )
        result = ait10.RecoveryResult(
            "account_disabled", "Your Account Is Disabled", "", "", ""
        )
        temp_root = Path(r"C:\Users\zhang\Desktop\codex_tmp")
        with tempfile.TemporaryDirectory(
            dir=temp_root, prefix="studentaid-quote-test-"
        ) as folder:
            output = Path(folder) / "result.csv"
            self.assertTrue(ait10.append_cumulative_result(output, item, result))
            raw = output.read_text(encoding="utf-8-sig")
            self.assertTrue(raw.startswith('"111-22-3333","01/02/1980"'))
            with output.open("r", encoding="utf-8-sig", newline="") as stream:
                row = next(csv.reader(stream))
            self.assertEqual(len(row), 9)
            self.assertEqual(row[1], "01/02/1980")

    def test_account_disabled_is_a_normal_explicit_result(self):
        class DisabledPage:
            def evaluate(self, _script):
                return "Your Account Is Disabled"

            def wait_for_timeout(self, _milliseconds):
                return None

        status = ait10.step_4_judge_password_recovery(
            DisabledPage(), threading.Event(), timeout_ms=100
        )
        self.assertEqual(status, "account_disabled")
        with patch.object(
            ait10, "_visible_text", return_value=ait10.ACCOUNT_DISABLED_HEADING
        ):
            result = ait10.collect_recovery_result(DisabledPage(), status)
        self.assertEqual(result.heading, "Your Account Is Disabled")
        self.assertEqual(result.masked_phone, "")
        self.assertEqual(result.masked_email, "")
        self.assertEqual(result.recovery_method, "")

    def test_atomic_replace_retries_transient_permission_error(self):
        with patch.object(
            ait10.os,
            "replace",
            side_effect=[PermissionError("busy"), None],
        ) as replace, patch.object(ait10.time, "sleep") as sleep:
            ait10._atomic_replace_with_retry(Path("source"), Path("target"))
        self.assertEqual(replace.call_count, 2)
        sleep.assert_called_once()

    def test_filled_form_timeout_is_retryable_page_stall(self):
        class Field:
            def select_option(self, _value):
                return None

            def press(self, _key):
                return None

        class FormPage:
            def locator(self, _selector):
                return Field()

            def wait_for_function(self, _script, timeout):
                raise TimeoutError(timeout)

            def wait_for_timeout(self, _milliseconds):
                return None

        details = SimpleNamespace(
            first_name="First",
            last_name="Last",
            birth_month="01",
            birth_day="02",
            birth_year="1980",
            ssn="111223333",
        )
        with patch.object(ait10, "_type_account_field"):
            with self.assertRaises(ait10.PageSubmissionStalled):
                ait10.step_2_fill_account_details(
                    FormPage(), details, threading.Event()
                )

    def test_result_timeout_is_retryable_page_stall(self):
        class EmptyPage:
            def evaluate(self, _script):
                return ""

            def wait_for_timeout(self, _milliseconds):
                return None

        with self.assertRaises(ait10.PageSubmissionStalled):
            ait10.step_4_judge_password_recovery(
                EmptyPage(), threading.Event(), timeout_ms=1
            )

    def test_three_digit_year_restores_leading_one(self):
        self.assertEqual(ait10._parse_dob("09/07/980"), ("09", "07", "1980"))

    def test_three_digit_year_restores_trailing_zero_when_unique(self):
        self.assertEqual(ait10._parse_dob("12/26/198"), ("12", "26", "1980"))

    def test_three_digit_year_is_only_restored_when_plausible(self):
        with self.assertRaises(ValueError):
            ait10._parse_dob("09/07/123")
        with self.assertRaises(ValueError):
            ait10._parse_dob("02/30/980")

    def test_any_missing_required_field_is_marked_for_direct_deletion(self):
        rows = (
            ["", "01", "02", "1980", "Last", "First", "Address"],
            ["111223333", "", "02", "1980", "Last", "First", "Address"],
            ["111223333", "01", "", "1980", "Last", "First", "Address"],
            ["111223333", "01", "02", "", "Last", "First", "Address"],
            ["111223333", "01", "02", "1980", "Last", "", "Address"],
            ["111223333", "01", "02", "1980", "", "First", "Address"],
        )
        for row in rows:
            with self.subTest(row=row):
                with self.assertRaises(ait10.MissingRequiredField):
                    ait10._parse_input_row(row, None)

    def test_normal_first_and_last_names_are_unchanged(self):
        details, _address = ait10._parse_input_row(
            ["111223333", "09/07/1980", "First", "Last", "Example Address"],
            None,
        )
        self.assertEqual(details.first_name, "First")
        self.assertEqual(details.last_name, "Last")

    def test_five_column_name_name_dob_order_is_detected(self):
        details, address = ait10._parse_input_row(
            ["111223333", "First", "Last", "01/02/1980", "Example Address"],
            None,
        )
        self.assertEqual(details.first_name, "First")
        self.assertEqual(details.last_name, "Last")
        self.assertEqual(details.birth_month, "01")
        self.assertEqual(details.birth_day, "02")
        self.assertEqual(details.birth_year, "1980")
        self.assertEqual(address, "Example Address")

    def test_current_failed_rows_remain_importable_for_retry(self):
        database = Path(r"C:\Users\zhang\Desktop\studentaid\studentaid.sqlite3")
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        try:
            batch_id = connection.execute(
                "select batch_id from batches order by created_at desc limit 1"
            ).fetchone()[0]
            rows = connection.execute(
                "select original_fields_json from records "
                "where batch_id=? and status='failed' order by id",
                (batch_id,),
            ).fetchall()
        finally:
            connection.close()
        if not rows:
            self.skipTest("当前最新批次没有失败残留")
        parsed = [
            ait10._parse_input_row(json.loads(original_fields_json), None)[0]
            for (original_fields_json,) in rows
        ]
        self.assertTrue(all(item.first_name and item.last_name for item in parsed))
        self.assertTrue(all(len(item.birth_year) == 4 for item in parsed))


if __name__ == "__main__":
    unittest.main()
