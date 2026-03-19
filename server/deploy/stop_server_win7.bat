@echo off
setlocal EnableExtensions
title KSQC Backend Win7 Stop

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "RUNTIME_DIR=%ROOT%\.runtime"
set "SERVER_PID_FILE=%RUNTIME_DIR%\backend.pid"
set "TARGET_PID="
set "PORT_OWNER="

call :resolve_target_pid
if not defined TARGET_PID (
    echo [OK] Backend is not running.
    del /q "%SERVER_PID_FILE%" >nul 2>&1
    if not defined NO_PAUSE timeout /t 2 >nul
    exit /b 0
)

echo [INFO] Stopping backend process PID %TARGET_PID% ...
taskkill /PID %TARGET_PID% /T /F >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to stop PID %TARGET_PID%.
    if not defined NO_PAUSE pause
    exit /b 1
)

timeout /t 1 >nul
call :get_port_owner
if defined PORT_OWNER if "%PORT_OWNER%"=="%TARGET_PID%" (
    echo [WARN] Port 5000 is still occupied, retrying...
    taskkill /PID %TARGET_PID% /T /F >nul 2>&1
    timeout /t 1 >nul
)

del /q "%SERVER_PID_FILE%" >nul 2>&1
echo [OK] Backend has been stopped.
if not defined NO_PAUSE timeout /t 2 >nul
exit /b 0

:resolve_target_pid
if exist "%SERVER_PID_FILE%" (
    set /p TARGET_PID=<"%SERVER_PID_FILE%"
    if defined TARGET_PID (
        tasklist /FI "PID eq %TARGET_PID%" | find "%TARGET_PID%" >nul 2>&1
        if not errorlevel 1 exit /b 0
        set "TARGET_PID="
    )
)

call :get_port_owner
if defined PORT_OWNER set "TARGET_PID=%PORT_OWNER%"
exit /b 0

:get_port_owner
set "PORT_OWNER="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":5000 .*LISTENING"') do (
    set "PORT_OWNER=%%P"
    goto :eof
)
exit /b 0
