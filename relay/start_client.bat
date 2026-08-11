@echo off
REM start_client.bat — start this machine's chat dashboard + agent bridge.
REM Reads relay_config.txt for RELAY_URL, TOKEN, ME, DASH_PORT.
setlocal
cd /d "%~dp0"
if not exist relay_config.txt (
  echo Missing relay_config.txt - copy relay_config.example.txt and fill in the values.
  exit /b 1
)
for /f "usebackq tokens=1,* delims==" %%a in ("relay_config.txt") do (
  if "%%a"=="RELAY_URL" set RELAY_URL=%%b
  if "%%a"=="TOKEN" set TOKEN=%%b
  if "%%a"=="ME" set ME=%%b
  if "%%a"=="DASH_PORT" set DASH_PORT=%%b
  if "%%a"=="WORKER_ENABLED" set WORKER_ENABLED=%%b
)
if "%DASH_PORT%"=="" set DASH_PORT=8788
echo Relay : %RELAY_URL%
echo Me    : %ME%

echo Starting chat dashboard on port %DASH_PORT% ...
start "chat-dashboard" cmd /c "python -u chat_feed.py --relay %RELAY_URL% --token %TOKEN% --me %ME% --port %DASH_PORT%"

echo Starting agent bridge ...
start "agent-bridge" cmd /c "python -u agent_bridge.py --relay %RELAY_URL% --token %TOKEN% --me %ME%"

REM Autonomous executor (runs mechanical board tasks without a session open).
if "%WORKER_ENABLED%"=="" set WORKER_ENABLED=0
if "%WORKER_ENABLED%"=="1" (
  echo Starting desktop worker ...
  start "desktop-worker" cmd /c "python -u desktop_worker.py --poll 5"
)
endlocal
