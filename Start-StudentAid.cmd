@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title StudentAid Standalone

set "APP_EXE=%~dp0StudentAid-Batch-Tool.exe"
if not exist "%APP_EXE%" (
    echo [ERROR] StudentAid-Batch-Tool.exe was not found.
    echo Extract every file from the release ZIP, then try again.
    pause
    exit /b 1
)

call :find_chrome
if not defined CHROME_PATH (
    echo [INSTALL] Google Chrome was not found. Installing with winget...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] winget is unavailable. Install Google Chrome, then run this file again.
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
    echo [ERROR] Google Chrome is still unavailable. Restart Windows or install Chrome manually.
    pause
    exit /b 1
)

echo [START] "%APP_EXE%"
start "" "%APP_EXE%"
exit /b 0

:find_chrome
set "CHROME_PATH="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME_PATH=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined CHROME_PATH if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME_PATH=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined CHROME_PATH if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME_PATH=%LocalAppData%\Google\Chrome\Application\chrome.exe"
exit /b 0
