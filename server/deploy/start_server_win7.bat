@echo off
setlocal EnableExtensions
title KSQC Backend Win7 Startup

echo ================================================
echo   KSQC Backend Startup ^(Win7 focused^)
echo ================================================
echo.

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "RUNTIME_DIR=%ROOT%\.runtime"
if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"
set "LOG_DIR=%RUNTIME_DIR%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%i"
set "LOG_FILE=%LOG_DIR%\backend_start_%TS%.log"
set "SERVER_STDOUT_LOG=%LOG_DIR%\backend_stdout_%TS%.log"
set "SERVER_STDERR_LOG=%LOG_DIR%\backend_stderr_%TS%.log"
set "SERVER_PID_FILE=%RUNTIME_DIR%\backend.pid"
set "LAUNCH_VBS=%RUNTIME_DIR%\launch_backend_hidden.vbs"
set "LAUNCH_CMD=%RUNTIME_DIR%\launch_backend_hidden.cmd"
set "SYSTEM_PYTHON="
for /f "delims=" %%i in ('where python 2^>nul') do if not defined SYSTEM_PYTHON set "SYSTEM_PYTHON=%%i"
set "SYSTEM_PYTHON_DIR="
if defined SYSTEM_PYTHON for %%I in ("%SYSTEM_PYTHON%") do set "SYSTEM_PYTHON_DIR=%%~dpI"
if defined SYSTEM_PYTHON_DIR if "%SYSTEM_PYTHON_DIR:~-1%"=="\" set "SYSTEM_PYTHON_DIR=%SYSTEM_PYTHON_DIR:~0,-1%"
set "SYSTEM_ENSUREPIP_DIR=%SYSTEM_PYTHON_DIR%\Lib\ensurepip\_bundled"
set "BUNDLED_SITE_PACKAGES=%ROOT%\python_deps"
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "RUN_PYTHON=%SYSTEM_PYTHON%"
set "USE_BUNDLED_DEPS=0"

call :ensure_not_running
if errorlevel 3 goto :port_conflict
if errorlevel 2 goto :already_running

if not defined SYSTEM_PYTHON (
    echo [ERROR] Python was not found.
    echo         Install Python 3.8.x 64-bit on Win7 and add it to PATH.
    goto :fail
)

set "PY_VER="
for /f "tokens=2 delims= " %%i in ('"%SYSTEM_PYTHON%" --version 2^>^&1') do set "PY_VER=%%i"
if "%PY_VER:~0,2%" NEQ "3." (
    echo [ERROR] Detected Python version: %PY_VER%
    echo         This backend bundle requires Python 3.8 or newer.
    goto :fail
)
if "%PY_VER:~0,3%"=="3.7" (
    echo [ERROR] Detected Python version: %PY_VER%
    echo         Python 3.7 is not supported by the current backend dependency chain.
    echo         Install Python 3.8 or newer.
    goto :fail
)
if "%PY_VER:~0,3%"=="3.8" set "USE_BUNDLED_DEPS=1"

if not exist "%ROOT%\server\data" mkdir "%ROOT%\server\data"
if not exist "%ROOT%\server\uploads" mkdir "%ROOT%\server\uploads"

if "%USE_BUNDLED_DEPS%"=="1" if exist "%BUNDLED_SITE_PACKAGES%\flask\__init__.py" (
    echo [1/3] Use bundled offline Python dependencies...
    >> "%LOG_FILE%" echo [%date% %time%] [1/3] Use bundled offline Python dependencies...
    set "PYTHONPATH=%BUNDLED_SITE_PACKAGES%;%PYTHONPATH%"
    "%RUN_PYTHON%" -c "import flask, flask_sqlalchemy, flask_jwt_extended, flask_cors, sqlalchemy, openpyxl, docx, apscheduler" >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo [ERROR] Bundled Python dependencies are incomplete.
        echo         Log: %LOG_FILE%
        goto :fail
    )
) else (
    if "%USE_BUNDLED_DEPS%"=="0" (
        echo [1/4] Detected Python %PY_VER%. Using a local virtual environment instead of Win7 offline deps...
        >> "%LOG_FILE%" echo [%date% %time%] [1/4] Detected Python %PY_VER%. Using a local virtual environment instead of Win7 offline deps...
    )
    call :ensure_venv
    if errorlevel 1 goto :fail
    set "RUN_PYTHON=%PYTHON%"

    echo [2/4] Prepare bootstrap toolchain...
    >> "%LOG_FILE%" echo [%date% %time%] [2/4] Prepare bootstrap toolchain...
    "%PYTHON%" -m pip --version >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        >> "%LOG_FILE%" echo [%date% %time%] [INFO] pip was not found in venv. Trying system pip bootstrap...
        "%SYSTEM_PYTHON%" -m pip --version >> "%LOG_FILE%" 2>&1
        if errorlevel 1 (
            >> "%LOG_FILE%" echo [%date% %time%] [WARN] System pip is unavailable. Falling back to ensurepip...
            "%PYTHON%" -m ensurepip >> "%LOG_FILE%" 2>&1
            if errorlevel 1 (
                echo [ERROR] Failed to initialize pip in the virtual environment.
                echo         Log: %LOG_FILE%
                goto :fail
            )
        ) else (
            if exist "%SYSTEM_ENSUREPIP_DIR%" (
                "%SYSTEM_PYTHON%" -m pip --python "%PYTHON%" install --no-index --find-links="%SYSTEM_ENSUREPIP_DIR%" pip setuptools >> "%LOG_FILE%" 2>&1
            ) else (
                "%SYSTEM_PYTHON%" -m pip --python "%PYTHON%" install --disable-pip-version-check --no-warn-script-location --upgrade pip setuptools >> "%LOG_FILE%" 2>&1
            )
            if errorlevel 1 (
                echo [ERROR] Failed to bootstrap pip from the system Python.
                echo         Log: %LOG_FILE%
                goto :fail
            )
        )
    )
    "%PYTHON%" -m pip install --disable-pip-version-check --no-warn-script-location --upgrade "setuptools==69.5.1" "wheel==0.42.0" >> "%LOG_FILE%" 2>&1
    if defined KSQC_UPGRADE_PIP (
        "%PYTHON%" -m pip install --disable-pip-version-check --no-warn-script-location --upgrade "pip==24.0" >> "%LOG_FILE%" 2>&1
    )
    if errorlevel 1 (
        echo [ERROR] Failed to install bootstrap packages.
        echo         Log: %LOG_FILE%
        goto :fail
    )

    echo [3/4] Install runtime dependencies...
    >> "%LOG_FILE%" echo [%date% %time%] [3/4] Install runtime dependencies...
    "%PYTHON%" -m pip install --disable-pip-version-check --no-warn-script-location -r "%ROOT%\server\requirements-win7.txt" >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo [ERROR] Failed to install backend dependencies.
        echo         Log: %LOG_FILE%
        goto :fail
    )
)

if exist "%ROOT%\frontend\dist\index.html" (
    echo [INFO] frontend\dist was found. Browser fallback pages are enabled.
) else (
    echo [INFO] frontend\dist was not found.
    echo        API and desktop client can still work.
    echo        Extract the frontend package next to this backend root if you need web pages.
)

echo.
echo [4/4] Start service...
echo   URL      : http://localhost:5000
echo   Default  : admin / admin123
echo.
>> "%LOG_FILE%" echo [%date% %time%] [4/4] Start service...
call :write_launcher_vbs
if errorlevel 1 goto :fail
call :start_hidden_process
if errorlevel 1 goto :fail

call :wait_for_server
if errorlevel 1 (
    echo [ERROR] Server process started but port 5000 is not ready.
    echo         Out: %SERVER_STDOUT_LOG%
    echo         Err: %SERVER_STDERR_LOG%
    >> "%LOG_FILE%" echo [%date% %time%] [ERROR] Port 5000 did not become ready.
    call :cleanup_failed_start
    goto :fail
)

call :capture_server_pid
if errorlevel 1 (
    echo [WARN] Backend started, but PID could not be captured.
    echo        stop_server.bat will still try to stop by port 5000.
    >> "%LOG_FILE%" echo [%date% %time%] [WARN] Failed to capture backend PID from port 5000.
)

echo [OK] Backend is running in background.
echo        Startup black window can now close.
echo        Out: %SERVER_STDOUT_LOG%
echo        Err: %SERVER_STDERR_LOG%
>> "%LOG_FILE%" echo [%date% %time%] [OK] Backend is running in background.
goto :end

:already_running
echo [OK] Backend is already running.
echo        URL: http://localhost:5000
>> "%LOG_FILE%" echo [%date% %time%] [OK] Backend is already running.
goto :end

:port_conflict
echo [ERROR] Port 5000 is occupied by another process.
echo         Run stop_server.bat first, or free the port manually.
>> "%LOG_FILE%" echo [%date% %time%] [ERROR] Port 5000 is occupied by another process.
goto :fail

:fail
echo.
if not defined NO_PAUSE pause
exit /b 1

:write_launcher_vbs
> "%LAUNCH_VBS%" echo Set shell = CreateObject("WScript.Shell")
>> "%LAUNCH_VBS%" echo shell.Run Chr(34) ^& "%LAUNCH_CMD%" ^& Chr(34), 0, False
if errorlevel 1 (
    echo [ERROR] Failed to create hidden launcher.
    echo         Log: %LOG_FILE%
    exit /b 1
)
> "%LAUNCH_CMD%" echo @echo off
>> "%LAUNCH_CMD%" echo cd /d "%ROOT%\server"
>> "%LAUNCH_CMD%" echo set "PYTHONUTF8=1"
>> "%LAUNCH_CMD%" echo set "PYTHONIOENCODING=utf-8"
>> "%LAUNCH_CMD%" echo set "PYTHONPATH=%PYTHONPATH%"
>> "%LAUNCH_CMD%" echo "%RUN_PYTHON%" run.py 1^>^>"%SERVER_STDOUT_LOG%" 2^>^>"%SERVER_STDERR_LOG%"
if errorlevel 1 (
    echo [ERROR] Failed to create hidden launcher command file.
    echo         Log: %LOG_FILE%
    exit /b 1
)
exit /b 0

:start_hidden_process
wscript.exe "%LAUNCH_VBS%"
if errorlevel 1 (
    echo [ERROR] Hidden backend launcher failed.
    echo         Log: %LOG_FILE%
    >> "%LOG_FILE%" echo [%date% %time%] [ERROR] Hidden backend launcher failed.
    exit /b 1
)
exit /b 0

:ensure_not_running
if not exist "%SERVER_PID_FILE%" (
    call :get_port_owner
    if defined PORT_OWNER exit /b 3
    exit /b 0
)

call :get_port_owner
set "EXISTING_PID="
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
    del /q "%SERVER_PID_FILE%" >nul 2>&1
    exit /b 3
)

del /q "%SERVER_PID_FILE%" >nul 2>&1
exit /b 0

:get_port_owner
set "PORT_OWNER="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":5000 .*LISTENING"') do (
    set "PORT_OWNER=%%P"
    goto :eof
)
exit /b 0

:wait_for_server
setlocal
for /l %%N in (1,1,20) do (
    call :get_port_owner
    if defined PORT_OWNER (
        endlocal
        exit /b 0
    )
    timeout /t 1 >nul
)
endlocal
exit /b 1

:cleanup_failed_start
if exist "%SERVER_PID_FILE%" (
    set "FAILED_PID="
    set /p FAILED_PID=<"%SERVER_PID_FILE%"
    if not "%FAILED_PID%"=="" taskkill /PID %FAILED_PID% /T /F >nul 2>&1
    del /q "%SERVER_PID_FILE%" >nul 2>&1
)
exit /b 0

:capture_server_pid
call :get_port_owner
if not defined PORT_OWNER exit /b 1
> "%SERVER_PID_FILE%" echo %PORT_OWNER%
exit /b 0

:ensure_venv
if not exist "%PYTHON%" goto :create_venv
"%PYTHON%" -c "import sys; print(sys.executable)" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [WARN] Existing .venv is invalid. Recreating...
    >> "%LOG_FILE%" echo [%date% %time%] [WARN] Existing .venv is invalid. Recreating...
    rd /s /q "%ROOT%\.venv" >> "%LOG_FILE%" 2>&1
    if exist "%ROOT%\.venv" (
        echo [ERROR] Failed to remove invalid .venv.
        echo         Log: %LOG_FILE%
        exit /b 1
    )
    goto :create_venv
)
exit /b 0

:create_venv
echo [1/4] Create virtual environment...
>> "%LOG_FILE%" echo [%date% %time%] [1/4] Create virtual environment...
"%SYSTEM_PYTHON%" -m venv "%ROOT%\.venv" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    echo         Log: %LOG_FILE%
    exit /b 1
)
exit /b 0

:end
if not defined NO_PAUSE pause
