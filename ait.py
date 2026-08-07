"""
StudentAid 浏览器自动化脚本。

当前已实现：
1. 启动可视化 Chrome 并打开 FSA ID 账户信息找回页面。
2. 填写 First Name、Last Name、出生日期和 Social Security Number。
3. 点击 Continue。
4. 判断账户是否可以找回登录信息。
5. 保留原始字段，并在末尾追加找回结果后写入纯文本 .scv 文件。
6. 结果明确后删除输入记录，并按输出第一列自动清理已完成记录。

说明：
- 默认优先读取当前运行目录的 studentaid_input.scv；文件不存在时再从环境变量或交互输入读取。
- SSN 不打印到日志；仅按要求作为原始字段写入结果文件。
- 后续步骤将在同一浏览器会话中继续补充。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from getpass import getpass
import os
from pathlib import Path
import re
from typing import Sequence

from playwright.sync_api import Browser, Page, Playwright, sync_playwright


RETRIEVE_ACCOUNT_DETAILS_URL = (
    "https://studentaid.gov/fsa-id/sign-in/retrieve-account-details"
)

FIRST_NAME_SELECTOR = "#fsa_Input_ForgotUsernameFirstName"
LAST_NAME_SELECTOR = "#fsa_Input_ForgotUsernameLastName"
BIRTH_MONTH_SELECTOR = "#fsa_Input_ForgotUsernameDateOfBirthMonth"
BIRTH_DAY_SELECTOR = "#fsa_Input_ForgotUsernameDateOfBirthDay"
BIRTH_YEAR_SELECTOR = "#fsa_Input_ForgotUsernameDateOfBirthYear"
SSN_SELECTOR = "#fsa_Input_ForgotUsernameSsnInput"


@dataclass(frozen=True)
class AccountDetails:
    """StudentAid 账户找回页面所需的个人资料。"""

    first_name: str
    last_name: str
    birth_month: str
    birth_day: str
    birth_year: str
    ssn: str
    original_ssn: str


def launch_browser(playwright: Playwright) -> Browser:
    """启动可视化浏览器，优先使用电脑中已安装的 Google Chrome。"""
    try:
        return playwright.chromium.launch(channel="chrome", headless=False)
    except Exception:
        # 未安装 Chrome 或当前 Playwright 不支持 Chrome channel 时，
        # 回退到 Playwright 自带的 Chromium。
        return playwright.chromium.launch(headless=False)


def step_1_open_retrieve_account_details(page: Page) -> None:
    """第一步：打开 StudentAid 的账户信息找回页面。"""
    page.goto(
        RETRIEVE_ACCOUNT_DETAILS_URL,
        wait_until="domcontentloaded",
        timeout=60_000,
    )
    page.locator(FIRST_NAME_SELECTOR).wait_for(state="visible", timeout=60_000)


def _read_value(env_name: str, prompt: str, *, secret: bool = False) -> str:
    """读取环境变量；未设置时再向用户询问，避免把资料写入源码。"""
    value = os.getenv(env_name, "").strip()
    if value:
        return value
    return (getpass(prompt) if secret else input(prompt)).strip()


def _normalise_month(value: str) -> str:
    """把月份数字或英文月份统一转换为 select 使用的 01-12。"""
    aliases = {
        "january": "01",
        "jan": "01",
        "february": "02",
        "feb": "02",
        "march": "03",
        "mar": "03",
        "april": "04",
        "apr": "04",
        "may": "05",
        "june": "06",
        "jun": "06",
        "july": "07",
        "jul": "07",
        "august": "08",
        "aug": "08",
        "september": "09",
        "sep": "09",
        "sept": "09",
        "october": "10",
        "oct": "10",
        "november": "11",
        "nov": "11",
        "december": "12",
        "dec": "12",
    }
    cleaned = value.strip().lower()
    month = aliases.get(cleaned) or (cleaned.zfill(2) if cleaned.isdigit() else "")
    if month not in {f"{number:02d}" for number in range(1, 13)}:
        raise ValueError("出生月份必须是 1-12、01-12 或英文月份名称。")
    return month


def _normalise_digits(value: str, field_name: str) -> str:
    """仅保留数字，并确保字段不为空。"""
    digits = re.sub(r"\D", "", value)
    if not digits:
        raise ValueError(f"{field_name}不能为空。")
    return digits


def load_account_details() -> AccountDetails:
    """读取并校验第二步所需资料；不保存或打印 SSN。"""
    first_name = _read_value("STUDENTAID_FIRST_NAME", "First Name: ")
    last_name = _read_value("STUDENTAID_LAST_NAME", "Last Name: ")
    month = _normalise_month(
        _read_value("STUDENTAID_BIRTH_MONTH", "Birth Month (1-12): ")
    )
    day = _normalise_digits(
        _read_value("STUDENTAID_BIRTH_DAY", "Birth Day: "), "出生日期（日）"
    ).zfill(2)
    year = _normalise_digits(
        _read_value("STUDENTAID_BIRTH_YEAR", "Birth Year: "), "出生日期（年）"
    )
    original_ssn = _read_value(
        "STUDENTAID_SSN", "Social Security Number: ", secret=True
    )
    ssn = _normalise_digits(original_ssn, "Social Security Number")

    if not first_name or len(first_name) > 35:
        raise ValueError("First Name 不能为空且长度不能超过 35 个字符。")
    if not last_name or len(last_name) > 35:
        raise ValueError("Last Name 不能为空且长度不能超过 35 个字符。")
    if len(day) != 2 or not 1 <= int(day) <= 31:
        raise ValueError("出生日期（日）必须是 1-31。")
    if len(year) != 4 or not 1900 <= int(year) <= date.today().year:
        raise ValueError("出生年份必须是四位数字，且不晚于当前年份。")
    try:
        date(int(year), int(month), int(day))
    except ValueError as exc:
        raise ValueError("出生日期不是有效日期。") from exc
    if len(ssn) != 9:
        raise ValueError("Social Security Number 必须包含 9 位数字。")

    return AccountDetails(
        first_name=first_name,
        last_name=last_name,
        birth_month=month,
        birth_day=day,
        birth_year=year,
        ssn=ssn,
        original_ssn=original_ssn,
    )


def step_2_fill_account_details(page: Page, details: AccountDetails) -> None:
    """第二步：按照页面字段 ID 填写账户资料。"""
    page.locator(FIRST_NAME_SELECTOR).fill(details.first_name)
    page.locator(LAST_NAME_SELECTOR).fill(details.last_name)
    page.locator(BIRTH_MONTH_SELECTOR).select_option(details.birth_month)
    page.locator(BIRTH_DAY_SELECTOR).fill(str(int(details.birth_day)))
    page.locator(BIRTH_YEAR_SELECTOR).fill(details.birth_year)
    page.locator(SSN_SELECTOR).fill(details.ssn)


def step_3_click_continue(page: Page) -> None:
    """第三步：点击页面中显示 Continue 文本的元素。"""
    # 页面实际结构为 <span>Continue</span>，使用精确文本定位，
    # 点击事件会沿 DOM 冒泡到其外层按钮或可点击容器。
    continue_element = page.get_by_text("Continue", exact=True).first
    continue_element.wait_for(state="visible", timeout=30_000)
    continue_element.click(timeout=30_000)


def step_4_judge_password_recovery(page: Page) -> str:
    """第四步：根据页面结果判断账户是否可以找回登录信息。

    返回值：
    - ``can_recover``：页面显示 Retrieve Your Log-in Information。
    - ``account_not_found``：页面显示 Account Not Found。
    - ``unknown``：页面结果尚未识别，避免误判。
    """
    page.wait_for_function(
        """
        () => {
            const text = document.body?.innerText || "";
            return text.includes("Retrieve Your Log-in Information")
                || text.includes("Account Not Found");
        }
        """,
        timeout=30_000,
    )

    account_not_found = page.get_by_text(
        re.compile(
            r"^\s*Account Not Found(?:\s*:\s*Create a New Account)?\s*$",
            re.IGNORECASE,
        )
    ).first
    if account_not_found.is_visible():
        return "account_not_found"

    recovery_header = page.get_by_text(
        "Retrieve Your Log-in Information", exact=True
    ).first
    if recovery_header.is_visible():
        return "can_recover"

    return "unknown"


@dataclass(frozen=True)
class RecoveryResult:
    """准备追加到输出记录末尾的页面找回结果。"""

    heading: str
    masked_phone: str
    masked_email: str
    recovery_method: str


def _visible_text(page: Page, text: str) -> str:
    """读取完全匹配的可见文本；不存在时返回空字符串。"""
    locator = page.get_by_text(text, exact=True).first
    if locator.is_visible():
        return locator.inner_text().strip()
    return ""


def collect_recovery_result(page: Page, recovery_status: str) -> RecoveryResult:
    """采集成功页面中的标题、脱敏手机、脱敏邮箱和 Photo ID 选项。"""
    if recovery_status == "account_not_found":
        not_found = page.get_by_text(
            re.compile(
                r"^\s*Account Not Found(?:\s*:\s*Create a New Account)?\s*$",
                re.IGNORECASE,
            )
        ).first
        heading = not_found.inner_text().strip() if not_found.is_visible() else "Account Not Found"
        return RecoveryResult(heading, "", "", "")

    heading = _visible_text(page, "Retrieve Your Log-in Information")
    masked_phone = ""
    masked_email = ""

    # 联系方式位于可见的 <p> 元素中。只读取页面已经脱敏的文本，
    # 不输出或推测完整电话号码、邮箱地址。
    for text in page.locator("p:visible").all_inner_texts():
        value = text.strip()
        if not value:
            continue
        if "@" in value and not masked_email:
            masked_email = value
        elif re.search(r"\d{4}\s*$", value) and not masked_phone:
            masked_phone = value

    recovery_method = _visible_text(page, "Recover my account with a photo ID")
    return RecoveryResult(
        heading=heading,
        masked_phone=masked_phone,
        masked_email=masked_email,
        recovery_method=recovery_method,
    )


def build_original_output_fields(details: AccountDetails) -> list[str]:
    """构建需要原样保留的输入字段。

    若设置 ``STUDENTAID_ORIGINAL_RECORD``，按一行 CSV/SCV 解析并完整保留
    其中的全部原始列；否则由当前交互输入构建基础字段。地址只作为原始列
    保留，不参与网页填写，可通过 ``STUDENTAID_ADDRESS`` 提供。
    """
    original_record = os.getenv("STUDENTAID_ORIGINAL_RECORD", "")
    if original_record:
        return next(csv.reader([original_record]))

    fields = [
        details.original_ssn,
        f"{details.birth_month}/{details.birth_day}/{details.birth_year}",
        details.first_name,
        details.last_name,
    ]
    address = os.getenv("STUDENTAID_ADDRESS", "").strip()
    if address:
        fields.append(address)
    return fields


def step_5_append_result_to_scv(
    original_fields: Sequence[str],
    recovery_result: RecoveryResult,
    output_path: Path,
) -> None:
    """第五步：保留原始列，并把四个结果列追加到一行末尾。

    文件扩展名严格按用户要求使用 ``.scv``；内容使用标准 CSV 纯文本格式，
    因而包含逗号的地址会自动加引号，不会被错误拆列。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file, lineterminator="\n")
        writer.writerow(
            [
                *original_fields,
                recovery_result.heading,
                recovery_result.masked_phone,
                recovery_result.masked_email,
                recovery_result.recovery_method,
            ]
        )
        # 先确保累计结果真正落盘，再删除输入记录，避免异常中断造成资料丢失。
        output_file.flush()
        os.fsync(output_file.fileno())


def _normalise_record_key(value: str) -> str:
    """规范化第一列记录键，使带连字符和纯数字 SSN 能互相匹配。"""
    stripped = value.strip()
    digits = re.sub(r"\D", "", stripped)
    if len(digits) == 9:
        return digits
    return stripped.casefold()


def _is_header_row(row: Sequence[str]) -> bool:
    """识别常见的第一行表头，避免把表头当作待处理资料。"""
    if not row:
        return False
    return row[0].strip().casefold() in {
        "ssn",
        "social security number",
        "social_security_number",
    }


def _read_scv_rows(path: Path) -> list[list[str]]:
    """读取纯文本 SCV/CSV；utf-8-sig 同时兼容带 BOM 和无 BOM 文件。"""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as source_file:
        return [list(row) for row in csv.reader(source_file)]


def _atomic_write_scv_rows(path: Path, rows: Sequence[Sequence[str]]) -> None:
    """在同目录写临时文件后原子替换，避免输入文件被写坏。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="") as temp_file:
            writer = csv.writer(temp_file, lineterminator="\n")
            writer.writerows(rows)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _completed_output_keys(output_path: Path) -> set[str]:
    """读取累计输出文件第一列，生成已经明确处理过的记录键集合。"""
    completed: set[str] = set()
    for row in _read_scv_rows(output_path):
        if not row or _is_header_row(row):
            continue
        key = _normalise_record_key(row[0])
        if key:
            completed.add(key)
    return completed


def remove_input_records_by_keys(input_path: Path, keys: set[str]) -> int:
    """从输入文件删除第一列命中 keys 的全部记录，其他列保持原值。"""
    if not input_path.exists() or not keys:
        return 0

    rows = _read_scv_rows(input_path)
    kept_rows: list[list[str]] = []
    removed_count = 0

    for row in rows:
        if not row or _is_header_row(row):
            kept_rows.append(row)
            continue
        key = _normalise_record_key(row[0])
        if key and key in keys:
            removed_count += 1
        else:
            kept_rows.append(row)

    if removed_count:
        _atomic_write_scv_rows(input_path, kept_rows)
    return removed_count


def remove_already_completed_input_records(
    input_path: Path, output_path: Path
) -> int:
    """启动时按输出第一列清理输入文件中已经完成的全部资料。"""
    return remove_input_records_by_keys(
        input_path,
        _completed_output_keys(output_path),
    )


def get_next_pending_row(input_path: Path) -> list[str] | None:
    """返回输入文件中第一条非空、非表头的待处理资料。"""
    for row in _read_scv_rows(input_path):
        if row and not _is_header_row(row) and any(value.strip() for value in row):
            return row
    return None


def account_details_from_input_row(row: Sequence[str]) -> AccountDetails:
    """按 SSN、DOB、First Name、Last Name、Address 的列顺序解析输入行。"""
    if len(row) < 4:
        raise ValueError("输入资料至少需要 4 列：SSN、DOB、First Name、Last Name。")

    original_ssn = row[0].strip()
    date_of_birth = row[1].strip()
    first_name = row[2].strip()
    last_name = row[3].strip()
    ssn = _normalise_digits(original_ssn, "Social Security Number")

    parsed_date = None
    for date_format in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d"):
        try:
            parsed_date = datetime.strptime(date_of_birth, date_format).date()
            break
        except ValueError:
            continue

    if parsed_date is None:
        raise ValueError(
            "输入文件 DOB 格式无效，应为 MM/DD/YYYY、MM-DD-YYYY 或 YYYY-MM-DD。"
        )
    if not first_name or len(first_name) > 35:
        raise ValueError("输入文件 First Name 不能为空且长度不能超过 35 个字符。")
    if not last_name or len(last_name) > 35:
        raise ValueError("输入文件 Last Name 不能为空且长度不能超过 35 个字符。")
    if len(ssn) != 9:
        raise ValueError("输入文件 Social Security Number 必须包含 9 位数字。")

    return AccountDetails(
        first_name=first_name,
        last_name=last_name,
        birth_month=f"{parsed_date.month:02d}",
        birth_day=f"{parsed_date.day:02d}",
        birth_year=f"{parsed_date.year:04d}",
        ssn=ssn,
        original_ssn=original_ssn,
    )


def main() -> None:
    data_directory = Path.cwd()
    input_path = Path(
        os.getenv(
            "STUDENTAID_INPUT_FILE",
            str(data_directory / "studentaid_input.scv"),
        )
    )
    output_path = Path(
        os.getenv(
            "STUDENTAID_OUTPUT_FILE",
            str(data_directory / "studentaid_results.scv"),
        )
    )

    if input_path.resolve() == output_path.resolve():
        raise ValueError("输入文件和输出文件不能是同一个文件。")

    pending_row: list[str] | None = None
    input_record_key = ""

    if input_path.exists():
        removed_before_run = remove_already_completed_input_records(
            input_path,
            output_path,
        )
        if removed_before_run:
            print(f"已从输入文件清理 {removed_before_run} 条历史完成资料。")

        pending_row = get_next_pending_row(input_path)
        if pending_row is None:
            print("输入文件中没有待处理资料。")
            return

        details = account_details_from_input_row(pending_row)
        original_fields = list(pending_row)
        input_record_key = _normalise_record_key(pending_row[0])
    else:
        # 输入文件不存在时保留原来的单条交互模式。
        details = load_account_details()
        original_fields = build_original_output_fields(details)

    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )
        page = context.new_page()

        try:
            step_1_open_retrieve_account_details(page)
            step_2_fill_account_details(page, details)
            step_3_click_continue(page)
            recovery_status = step_4_judge_password_recovery(page)
            recovery_result = collect_recovery_result(page, recovery_status)

            if recovery_status == "can_recover":
                print("判断结果：可以找回密码/登录信息。")
            elif recovery_status == "account_not_found":
                print("判断结果：账户未找到，当前无法找回密码/登录信息。")
            else:
                print("判断结果：暂未识别页面结果，本条资料不会输出或删除。")

            if recovery_status in {"can_recover", "account_not_found"}:
                # 输出文件只追加、不覆盖。输出落盘成功后，才删除输入资料。
                step_5_append_result_to_scv(
                    original_fields,
                    recovery_result,
                    output_path,
                )
                print(f"结果已追加到：{output_path}")

                if input_record_key:
                    removed_after_result = remove_input_records_by_keys(
                        input_path,
                        {input_record_key},
                    )
                    print(
                        f"已从输入文件删除 {removed_after_result} 条明确完成资料。"
                    )

            # 后续步骤将依次添加到这里，确保复用当前 page 和浏览器会话。
            input("第六步已完成。按 Enter 键关闭浏览器……")
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()










