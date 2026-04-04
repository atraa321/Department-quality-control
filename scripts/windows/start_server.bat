@echo off
setlocal EnableExtensions
title KSQC Server Launcher

set "NO_PAUSE="
if /I "%~1"=="--nopause" set "NO_PAUSE=1"

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\..") do set "ROOT=%%~fI"
set "RUNTIME_DIR=%ROOT%\.runtime"
if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"
set "LOG_DIR=%RUNTIME_DIR%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%i"
set "LOG_FILE=%LOG_DIR%\server_start_%TS%.log"
set "SERVER_STDOUT_LOG=%LOG_DIR%\server_stdout_%TS%.log"
set "SERVER_STDERR_LOG=%LOG_DIR%\server_stderr_%TS%.log"
set "SERVER_PID_FILE=%RUNTIME_DIR%\server.pid"

call :ensure_not_running
if errorlevel 3 goto :port_conflict
if errorlevel 2 goto :already_running

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found. Install Python 3.10+ first.
    >> "%LOG_FILE%" echo [%date% %time%] [ERROR] Python was not found.
    if not defined NO_PAUSE pause
    exit /b 1
)

if not exist "%ROOT%\.venv\Scripts\python.exe" (
    echo [1/4] Create virtual environment...
    >> "%LOG_FILE%" echo [%date% %time%] [1/4] Create virtual environment...
    python -m venv "%ROOT%\.venv" >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo [ERROR] Virtual environment creation failed. Log: %LOG_FILE%
        >> "%LOG_FILE%" echo [%date% %time%] [ERROR] Virtual environment creation failed.
        if not defined NO_PAUSE pause
        exit /b 1
    )
)

set "PYTHON=%ROOT%\.venv\Scripts\python.exe"

if not exist "%ROOT%\server\data" mkdir "%ROOT%\server\data"
if not exist "%ROOT%\server\uploads" mkdir "%ROOT%\server\uploads"

echo [2/4] Install or update backend dependencies...
>> "%LOG_FILE%" echo [%date% %time%] [2/4] Install or update backend dependencies...
"%PYTHON%" -m pip install --upgrade pip >> "%LOG_FILE%" 2>&1
"%PYTHON%" -m pip install -r "%ROOT%\server\requirements.txt" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [ERROR] Backend dependency install failed. Log: %LOG_FILE%
    >> "%LOG_FILE%" echo [%date% %time%] [ERROR] Backend dependency install failed.
    if not defined NO_PAUSE pause
    exit /b 1
)

if not exist "%ROOT%\frontend\dist\index.html" (
    echo [3/4] Build frontend assets...
    >> "%LOG_FILE%" echo [%date% %time%] [3/4] Build frontend assets...
    where npm >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] npm was not found.
        >> "%LOG_FILE%" echo [%date% %time%] [ERROR] npm was not found.
        if not defined NO_PAUSE pause
        exit /b 1
    )

    pushd "%ROOT%\frontend"
    if not exist "node_modules" (
        call npm install >> "%LOG_FILE%" 2>&1
        if errorlevel 1 (
            popd
            echo [ERROR] npm install failed. Log: %LOG_FILE%
            >> "%LOG_FILE%" echo [%date% %time%] [ERROR] npm install failed.
            if not defined NO_PAUSE pause
            exit /b 1
        )
    )

    call npm run build >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        popd
        echo [ERROR] frontend build failed. Log: %LOG_FILE%
        >> "%LOG_FILE%" echo [%date% %time%] [ERROR] frontend build failed.
        if not defined NO_PAUSE pause
        exit /b 1
    )
    popd
)

echo [4/4] Start server...
echo   URL: http://localhost:5000
echo.
>> "%LOG_FILE%" echo [%date% %time%] [4/4] Start server...

cd /d "%ROOT%\server"
set "KSQC_PYTHON=%PYTHON%"
set "KSQC_SERVER_DIR=%ROOT%\server"
set "KSQC_SERVER_STDOUT=%SERVER_STDOUT_LOG%"
set "KSQC_SERVER_STDERR=%SERVER_STDERR_LOG%"
set "KSQC_SERVER_PID_FILE=%SERVER_PID_FILE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Start-Process -FilePath $env:KSQC_PYTHON -ArgumentList 'run.py' -WorkingDirectory $env:KSQC_SERVER_DIR -WindowStyle Hidden -RedirectStandardOutput $env:KSQC_SERVER_STDOUT -RedirectStandardError $env:KSQC_SERVER_STDERR -PassThru; [System.IO.File]::WriteAllText($env:KSQC_SERVER_PID_FILE, [string]$p.Id)"
if errorlevel 1 (
    echo [ERROR] Background server start failed. Log: %LOG_FILE%
    >> "%LOG_FILE%" echo [%date% %time%] [ERROR] Background server start failed.
    if not defined NO_PAUSE pause
    exit /b 1
)

call :wait_for_server
if errorlevel 1 (
    echo [ERROR] Server process started but port 5000 is not ready.
    echo Logs: %SERVER_STDOUT_LOG% ^| %SERVER_STDERR_LOG%
    >> "%LOG_FILE%" echo [%date% %time%] [ERROR] Port 5000 did not become ready.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo [OK] Server is running in background.
echo Log: %LOG_FILE%
echo Out: %SERVER_STDOUT_LOG%
echo Err: %SERVER_STDERR_LOG%
>> "%LOG_FILE%" echo [%date% %time%] [OK] Server is running in background.
if not defined NO_PAUSE ping 127.0.0.1 -n 3 >nul
exit /b 0

:already_running
echo [OK] Server is already running in background.
>> "%LOG_FILE%" echo [%date% %time%] [OK] Server is already running in background.
if not defined NO_PAUSE ping 127.0.0.1 -n 3 >nul
exit /b 0

:port_conflict
echo [ERROR] Port 5000 is occupied by another process.
>> "%LOG_FILE%" echo [%date% %time%] [ERROR] Port 5000 is occupied by another process.
if not defined NO_PAUSE pause
exit /b 1

:ensure_not_running
if not exist "%SERVER_PID_FILE%" (
    call :get_port_owner
    if defined PORT_OWNER (
        call :is_our_server_pid "%PORT_OWNER%"
        if not errorlevel 1 (
            > "%SERVER_PID_FILE%" echo %PORT_OWNER%
            exit /b 2
        )
        exit /b 3
    )
    exit /b 0
)

call :get_port_owner
set /p EXISTING_PID=<"%SERVER_PID_FILE%"
if "%EXISTING_PID%"=="" (
    del /q "%SERVER_PID_FILE%" >nul 2>&1
    if defined PORT_OWNER exit /b 3
    exit /b 0
)

tasklist /FI "PID eq %EXISTING_PID%" | find "%EXISTING_PID%" >nul 2>&1
if errorlevel 1 (
    del /q "%SERVER_PID_FILE%" >nul 2>&1
    if defined PORT_OWNER exit /b 3
    exit /b 0
)

if defined PORT_OWNER (
    if "%PORT_OWNER%"=="%EXISTING_PID%" exit /b 2
    call :is_our_server_pid "%PORT_OWNER%"
    if not errorlevel 1 exit /b 2
    del /q "%SERVER_PID_FILE%" >nul 2>&1
    exit /b 3
)

del /q "%SERVER_PID_FILE%" >nul 2>&1
exit /b 0

:is_our_server_pid
for /f %%A in ("%~1") do set "CHECK_PID=%%~A"
if "%CHECK_PID%"=="" exit /b 1
tasklist /FI "PID eq %CHECK_PID%" | find /I "python.exe" >nul 2>&1
if not errorlevel 1 exit /b 0
tasklist /FI "PID eq %CHECK_PID%" | find /I "pythonw.exe" >nul 2>&1
if not errorlevel 1 exit /b 0
exit /b 1

:get_port_owner
set "PORT_OWNER="
for /f %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-NetTCPConnection -State Listen -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess)"') do (
    set "PORT_OWNER=%%P"
    goto :eof
)
exit /b 0

:wait_for_server
setlocal
for /l %%N in (1,1,20) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/' -UseBasicParsing -TimeoutSec 2; exit 0 } catch { if ($_.Exception.Response) { exit 0 } else { exit 1 } }" >nul 2>&1
    if not errorlevel 1 (
        endlocal
        exit /b 0
    )
    ping 127.0.0.1 -n 2 >nul
)
endlocal
exit /b 1
