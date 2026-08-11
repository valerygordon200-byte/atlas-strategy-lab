@echo off
REM setup.bat — one-command setup for the dourmouse+atlas commercial stack (Windows).
REM 1. clones the repo (or pulls), 2. installs Python deps, 3. creates config from
REM    the example, 4. runs the smoke test (health_check.py) as the done-gate.
REM The data drive (E:\forex-data) must be attached; the stack lives where the
REM data lives — this script configures, it does not download datasets.
setlocal
set REPO_URL=https://github.com/valerygordon200-byte/atlas-strategy-lab.git
set DIR=%~dp0
cd /d "%DIR%"

echo === [1/4] repo ===
if not exist .git (
  echo cloning %REPO_URL%
  git clone %REPO_URL% .
) else (
  git pull --ff-only
)
if errorlevel 1 ( echo FAILED: repo step & exit /b 1 )

echo === [2/4] dependencies ===
if exist requirements.txt (
  python -m pip install -r requirements.txt --quiet
)
if errorlevel 1 ( echo FAILED: deps step & exit /b 1 )

echo === [3/4] config ===
if not exist relay\relay_config.txt (
  copy relay\relay_config.example.txt relay\relay_config.txt >nul
  echo created relay_config.txt from example - EDIT THE TOKEN before going live.
) else (
  echo relay_config.txt already present
)

echo === [4/4] smoke test ===
python E:\forex-data\scripts\health_check.py
if errorlevel 1 ( echo SMOKE TEST FAILED - stack not ready & exit /b 1 )

echo.
echo SETUP COMPLETE. Next:
echo   python scripts\pipeline_supervisor.py   (keeps everything alive, :8792)
echo   open http://127.0.0.1:8791/hub.html     (the commercial hub)
endlocal
