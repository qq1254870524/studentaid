@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title StudentAid Step 22 Account Not Found Full Status - Install and Start
set "PYTHONDONTWRITEBYTECODE=1"

if not exist "%~dp0ait17.py" (
    echo [ERROR] ait17.py is missing from this directory.
    pause
    exit /b 1
)
if not exist "%~dp0requirements.txt" (
    echo [ERROR] requirements.txt is missing from this directory.
    pause
    exit /b 1
)

call :find_python
if not defined PY_RUN (
    echo [INSTALL] Python 3.11+ was not found. Installing Python 3.12 with winget...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] winget is unavailable. Install Python 3.11+ and run this file again.
        pause
        exit /b 1
    )
    winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo [ERROR] Python installation failed.
        pause
        exit /b 1
    )
    call :find_python
)
if not defined PY_RUN (
    echo [ERROR] Python was installed but is not visible in this window. Run this file again.
    pause
    exit /b 1
)

call :find_chrome
if not defined CHROME_PATH (
    echo [INSTALL] Google Chrome was not found. Installing it with winget...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] winget is unavailable. Install Google Chrome and run this file again.
        pause
        exit /b 1
    )
    winget install --id Google.Chrome -e --source winget --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo [ERROR] Google Chrome installation failed.
        pause
        exit /b 1
    )
    call :find_chrome
)
if not defined CHROME_PATH (
    echo [ERROR] chrome.exe is still unavailable. Run this file again after Chrome setup finishes.
    pause
    exit /b 1
)

set "VENV_DIR=%~dp0.venv"
set "APP_PY=%VENV_DIR%\Scripts\python.exe"
set "APP_PYW=%VENV_DIR%\Scripts\pythonw.exe"
if not exist "%APP_PY%" (
    echo [INSTALL] Creating isolated Python environment...
    %PY_RUN% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create the isolated Python environment.
        pause
        exit /b 1
    )
) else (
    echo [SKIP] Isolated Python environment already exists.
)
if not exist "%APP_PYW%" (
    echo [ERROR] pythonw.exe is missing from the isolated Python environment.
    pause
    exit /b 1
)

"%APP_PY%" -c "import tkinter, playwright, openpyxl; from browser_use.browser.profile import BrowserProfile" >nul 2>&1
if errorlevel 1 (
    echo [INSTALL] Python dependencies are incomplete. Installing missing packages...
    "%APP_PY%" -m pip install --disable-pip-version-check -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo [ERROR] Python dependency installation failed.
        pause
        exit /b 1
    )
) else (
    echo [SKIP] Tkinter, Playwright, openpyxl, and browser-use are already available.
)

"%APP_PY%" -c "import tkinter, playwright, openpyxl; from browser_use.browser.profile import BrowserProfile" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Dependency verification failed.
    pause
    exit /b 1
)

if /i "%STUDENTAID_INSTALL_ONLY%"=="1" (
    echo [OK] Installation verification passed. GUI launch skipped by STUDENTAID_INSTALL_ONLY.
    exit /b 0
)

echo [START] Google Chrome: %CHROME_PATH%
echo [START] StudentAid Step 22 Account Not Found Full Status...
start "" "%APP_PYW%" -B "%~dp0ait17.py"
exit /b 0

:find_python
set "PY_RUN="
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_RUN=py -3"
)
if defined PY_RUN exit /b 0
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_RUN=python"
)
exit /b 0

:find_chrome
set "CHROME_PATH="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME_PATH=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined CHROME_PATH if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME_PATH=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined CHROME_PATH if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME_PATH=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if not defined CHROME_PATH for /f "tokens=2,*" %%A in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve 2^>nul ^| find /i "REG_SZ"') do set "CHROME_PATH=%%B"
if not defined CHROME_PATH for /f "tokens=2,*" %%A in ('reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve 2^>nul ^| find /i "REG_SZ"') do set "CHROME_PATH=%%B"
exit /b 0
