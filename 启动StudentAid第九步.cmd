@echo off
setlocal
cd /d "%~dp0"
set "PYTHONDONTWRITEBYTECODE=1"
set "STUDENTAID_CDP_URL=http://127.0.0.1:9223"

powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:9223/json/version' -TimeoutSec 2; if($r.StatusCode -eq 200){exit 0}else{exit 1} } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    if exist "%CHROME%" (
        start "" "%CHROME%" --remote-debugging-port=9223 --remote-debugging-address=127.0.0.1 --user-data-dir="%USERPROFILE%\.studentaid-chrome" "https://studentaid.gov/fsa-id/sign-in/retrieve-account-details"
        timeout /t 5 /nobreak >nul
    )
)

python -B "%~dp0ait4.py"
if errorlevel 1 (
    echo.
    echo StudentAid step 9 exited with an error.
    pause
)
endlocal