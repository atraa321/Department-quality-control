@echo off
chcp 65001 >nul
setlocal EnableExtensions
title 科室质控平台客户端启动器

echo ================================================
echo   科室质控平台 - 桌面客户端启动
echo ================================================
echo.

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\..") do set "ROOT=%%~fI"
set "RUNTIME_DIR=%ROOT%\.runtime"
if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"
set "LOG_DIR=%RUNTIME_DIR%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%i"
set "LOG_FILE=%LOG_DIR%\client_start_%TS%.log"
set "CLIENT_PID_FILE=%RUNTIME_DIR%\client.pid"

call :ensureNotRunning "%CLIENT_PID_FILE%" "客户端"
if errorlevel 2 (
    echo [状态] 客户端后台进程已存在。
    echo 客户端已在后台运行，无需重复启动。
    (
    echo [%date% %time%] [状态] 客户端后台进程已存在。
    echo [%date% %time%] 客户端已在后台运行，无需重复启动。
    )>> "%LOG_FILE%"
    timeout /t 2 >nul
    exit /b 0
)

if not exist "%ROOT%\.venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境，请先运行 启动服务器.bat 或手动创建 .venv
    >> "%LOG_FILE%" echo [%date% %time%] [错误] 未找到虚拟环境，请先运行 启动服务器.bat 或手动创建 .venv
    pause
    exit /b 1
)

set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "PYTHONW=%ROOT%\.venv\Scripts\pythonw.exe"

echo [1/2] 检查客户端依赖...
>> "%LOG_FILE%" echo [%date% %time%] [1/2] 检查客户端依赖...
"%PYTHON%" -m pip install -r "%ROOT%\client\requirements.txt" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [错误] 客户端依赖安装失败，日志：%LOG_FILE%
    >> "%LOG_FILE%" echo [%date% %time%] [错误] 客户端依赖安装失败，日志：%LOG_FILE%
    pause
    exit /b 1
)

echo [2/2] 启动客户端...
>> "%LOG_FILE%" echo [%date% %time%] [2/2] 启动客户端...
cd /d "%ROOT%"
if exist "%PYTHONW%" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Start-Process -FilePath '%PYTHONW%' -ArgumentList 'client\main.py','--start-hidden' -WorkingDirectory '%ROOT%' -WindowStyle Hidden -PassThru; Set-Content -Path '%RUNTIME_DIR%\client.pid' -Value $p.Id" >> "%LOG_FILE%" 2>&1
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Start-Process -FilePath '%PYTHON%' -ArgumentList 'client\main.py','--start-hidden' -WorkingDirectory '%ROOT%' -WindowStyle Hidden -RedirectStandardOutput '%LOG_FILE%' -RedirectStandardError '%LOG_FILE%' -PassThru; Set-Content -Path '%RUNTIME_DIR%\client.pid' -Value $p.Id" >> "%LOG_FILE%" 2>&1
)
if errorlevel 1 (
    echo.
    echo [错误] 客户端后台启动失败，请检查运行环境。日志：%LOG_FILE%
    (
    echo [%date% %time%].
    echo [%date% %time%] [错误] 客户端后台启动失败，请检查运行环境。日志：%LOG_FILE%
    )>> "%LOG_FILE%"
    pause
    exit /b 1
)

echo [状态] 客户端后台启动成功。
echo 客户端已在后台启动。
echo 如需停止，请运行 退出运行.bat
echo 日志文件：%LOG_FILE%
(
echo [%date% %time%] [状态] 客户端后台启动成功。
echo [%date% %time%] 客户端已在后台启动。
echo [%date% %time%] 如需停止，请运行 退出运行.bat
echo [%date% %time%] 日志文件：%LOG_FILE%
)>> "%LOG_FILE%"
timeout /t 2 >nul
exit /b 0

:ensureNotRunning
set "PIDFILE=%~1"
set "LABEL=%~2"
if not exist "%PIDFILE%" exit /b 0

set /p EXISTING_PID=<"%PIDFILE%"
if "%EXISTING_PID%"=="" (
    >> "%LOG_FILE%" echo [%date% %time%] [状态] 检测到空的客户端 PID 标记，已自动清理。
    del /q "%PIDFILE%" >nul 2>&1
    exit /b 0
)

tasklist /FI "PID eq %EXISTING_PID%" | find "%EXISTING_PID%" >nul 2>&1
if errorlevel 1 (
    >> "%LOG_FILE%" echo [%date% %time%] [状态] 检测到失效的客户端 PID 标记，已自动清理。
    del /q "%PIDFILE%" >nul 2>&1
    exit /b 0
)

exit /b 2
