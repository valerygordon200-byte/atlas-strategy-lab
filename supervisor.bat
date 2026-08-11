@echo off
rem supervisor.bat — one-shot, idempotent launcher for the pipeline supervisor.
rem Copied into the user Startup folder so the whole commercial stack
rem (relay/feed/worker/bridge/engine/hub/notify) comes back at logon
rem without admin rights. Skips if a supervisor is already running.
cd /d "C:\Users\ankit\Documents\forex-engine\atlas-strategy-lab"
wmic process where "name='python.exe'" get CommandLine 2>nul | findstr /I "pipeline_supervisor" >nul 2>&1
if %ERRORLEVEL%==0 (
  rem supervisor already running — do nothing
  exit /b 0
)
start /b python -u scripts/pipeline_supervisor.py >> .supervisor.log 2>&1
