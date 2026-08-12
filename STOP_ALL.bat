@echo off
REM ============================================================
REM  STOP_ALL.bat - stop every dourmouse/atlas stack process.
REM  Matches by command-line pattern so only stack processes die;
REM  unrelated python processes (and Ollama) are left alone.
REM ============================================================
setlocal
echo Stopping dourmouse + atlas stack...

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'pipeline_supervisor|autonomous_worker|relay_server|chat_feed|desktop_worker|agent_bridge|engine_api|serve_hub|notify_watch|event_watcher|watch_dourmouse|dourmouse\.webui' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('   killed ' + $_.ProcessId + '  ' + ($_.CommandLine -replace '.*\\python\.exe','')) }"

echo.
echo All stack processes stopped.  (Ollama was left running.)
endlocal
