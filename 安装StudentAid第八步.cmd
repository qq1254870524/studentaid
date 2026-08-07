@echo off
setlocal
cd /d "%~dp0"
set "PYTHONDONTWRITEBYTECODE=1"
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto :error
python -m playwright install chromium
if errorlevel 1 goto :error
echo.
echo StudentAid ??????????
pause
exit /b 0
:error
echo.
echo ???????????????
pause
exit /b 1
