"""Frozen-build dependency self-test; inactive during normal application startup."""

import json
import os
from pathlib import Path
import traceback


if os.environ.get("STUDENTAID_EXE_SELFTEST") == "1":
    output_path = os.environ.get("STUDENTAID_EXE_SELFTEST_OUTPUT", "")
    result = {
        "status": "failed",
        "tkinter": False,
        "openpyxl": False,
        "playwright": False,
        "playwright_driver": False,
        "browser_use": False,
    }
    exit_code = 1
    try:
        import tkinter  # noqa: F401
        import openpyxl
        import playwright  # noqa: F401
        from browser_use.browser.chrome import find_chrome_executable
        from browser_use.browser.profile import BrowserProfile  # noqa: F401
        from playwright.sync_api import sync_playwright

        result["tkinter"] = True
        result["openpyxl"] = True
        result["openpyxl_version"] = openpyxl.__version__
        result["playwright"] = True
        result["browser_use"] = True
        result["chrome_detected"] = bool(find_chrome_executable())

        driver = sync_playwright().start()
        try:
            result["playwright_driver"] = bool(driver.chromium)
        finally:
            driver.stop()

        result["status"] = "ok"
        exit_code = 0
    except BaseException:
        result["traceback"] = traceback.format_exc()
    finally:
        if output_path:
            Path(output_path).write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        os._exit(exit_code)
