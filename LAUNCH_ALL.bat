@echo off
REM ============================================================
REM  LAUNCH_ALL.bat  -  one-click start of the ENTIRE stack
REM  Dourmouse webui + push watcher   |   Atlas relay / feed /
REM  worker / bridge / engine / hub / notify / autonomous worker
REM  |   Forex calendar watcher (pen drive)
REM
REM  Idempotent: running it again restarts everything cleanly.
REM ============================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo  ============================================
echo    DOURMOUSE  //  FULL STACK LAUNCHER
echo  ============================================
echo.

if exist "E:\forex-data\scripts\event_watcher.py" (
  echo  [ok] Pen drive E:\forex-data present - calendar watcher included
) else (
  echo  [!!] Pen drive E:\forex-data NOT FOUND
  echo       The calendar watcher will be skipped until the drive is connected.
)

rem ---- 1. clean slate: stop anything already running ----
echo.
echo  [1/4] Stopping any existing stack processes...
call "%~dp0STOP_ALL.bat" >nul 2>&1
ping -n 4 127.0.0.1 >nul

rem ---- 2. start the pipeline supervisor (supervises all 11 services) ----
echo  [2/4] Starting pipeline supervisor...
cd /d "%~dp0"
start "dourmouse-supervisor" /min cmd /c "python -u scripts/pipeline_supervisor.py >> .supervisor.log 2>&1"

rem ---- 3. wait until EVERY service reports UP ----
echo  [3/4] Waiting for the stack to come online...
set /a tries=0
:waitloop
set /a tries+=1
if !tries! gtr 60 (
  echo  [!!] Timed out waiting for the stack.
  echo       Check atlas-strategy-lab\.supervisor.log for errors.
  goto status
)
ping -n 4 127.0.0.1 >nul
python -c "import json,urllib.request;d=json.load(urllib.request.urlopen('http://127.0.0.1:8792/status',timeout=2));import sys;sys.exit(0 if all(v['up'] for v in d['services'].values()) else 1)" >nul 2>&1
if errorlevel 1 goto waitloop
echo  [ok] All services report UP.

rem ---- 4. print status + open the hub ----
:status
echo.
echo  ============================================
echo    STACK STATUS  (http://127.0.0.1:8792/status)
echo  ============================================
python -c "import json,urllib.request;d=json.load(urllib.request.urlopen('http://127.0.0.1:8792/status',timeout=2));[print('   ' + k.ljust(12) + ('UP' if v['up'] else 'DOWN')) for k,v in d['services'].items()]" 2>nul
echo.
start "" http://127.0.0.1:8791/hub.html
echo  Hub opened:  http://127.0.0.1:8791/hub.html
echo  Chat feed:   http://127.0.0.1:8788
echo  Webui:       http://127.0.0.1:8765
echo.
endlocal
