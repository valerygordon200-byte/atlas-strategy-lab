@echo off
REM start_relay.bat — run the relay server (on the always-on machine, e.g. the laptop).
REM Usage:  start_relay.bat [port]   (default 8787)
setlocal
cd /d "%~dp0"
if "%1"=="" (set PORT=8787) else (set PORT=%1)

if not exist relay_config.txt (
  echo Missing relay_config.txt - copy relay_config.example.txt and fill in TOKEN.
  exit /b 1
)
for /f "usebackq tokens=1,* delims==" %%a in ("relay_config.txt") do (
  if "%%a"=="TOKEN" set TOKEN=%%b
)
echo Starting relay on port %PORT% ...
python -u relay_server.py --port %PORT% --token %TOKEN%
endlocal
