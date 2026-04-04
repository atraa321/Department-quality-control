@echo off
chcp 65001 >nul
setlocal EnableExtensions
title 科室质控平台退出

set "NO_PAUSE="
if /I "%~1"=="--nopause" set "NO_PAUSE=1"

echo ================================================
echo   科室质控平台 - 停止后台运行
echo ================================================
echo.

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\..") do set "ROOT=%%~fI"
set "RUNTIME_DIR=%ROOT%\.runtime"
set "LOG_DIR=%RUNTIME_DIR%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%i"
set "LOG_FILE=%LOG_DIR%\stop_all_%TS%.log"

if not exist "%RUNTIME_DIR%" (
    echo [状态] 当前没有后台运行标记。
    echo 未找到运行标记目录，无需停止。
    (
    echo [%date% %time%] [状态] 当前没有后台运行标记。
    echo [%date% %time%] 未找到运行标记目录，无需停止。
    )>> "%LOG_FILE%"
    if not defined NO_PAUSE pause
    exit /b 0
)

call :stop_by_pid_file "%RUNTIME_DIR%\server.pid" "服务端"
call :stop_by_pid_file "%RUNTIME_DIR%\client.pid" "客户端"

echo.
echo 处理完成。
echo 日志文件：%LOG_FILE%
(
echo [%date% %time%].
echo [%date% %time%] 处理完成。
echo [%date% %time%] 日志文件：%LOG_FILE%
)>> "%LOG_FILE%"
for %%D in ("%RUNTIME_DIR%") do rd "%%~fD" 2>nul
if not defined NO_PAUSE pause
exit /b 0

:stop_by_pid_file
set "PIDFILE=%~1"
set "LABEL=%~2"

if not exist "%PIDFILE%" (
    echo [状态] %LABEL% 当前没有后台运行记录。
    echo %LABEL% 未记录 PID，跳过。
    (
    echo [%date% %time%] [状态] %LABEL% 当前没有后台运行记录。
    echo [%date% %time%] %LABEL% 未记录 PID，跳过。
    )>> "%LOG_FILE%"
    goto :eof
)

set /p PID=<"%PIDFILE%"
if "%PID%"=="" (
    echo [状态] %LABEL% PID 标记为空，已清理。
    echo %LABEL% PID 为空，跳过。
    (
    echo [%date% %time%] [状态] %LABEL% PID 标记为空，已清理。
    echo [%date% %time%] %LABEL% PID 为空，跳过。
    )>> "%LOG_FILE%"
    del /q "%PIDFILE%" >nul 2>&1
    goto :eof
)

tasklist /FI "PID eq %PID%" | find "%PID%" >nul 2>&1
if errorlevel 1 (
    echo [状态] %LABEL% 进程已不存在，已清理旧标记。
    echo %LABEL% 进程不存在，清理标记。
    (
    echo [%date% %time%] [状态] %LABEL% 进程已不存在，已清理旧标记。
    echo [%date% %time%] %LABEL% 进程不存在，清理标记。
    )>> "%LOG_FILE%"
    del /q "%PIDFILE%" >nul 2>&1
    goto :eof
)

taskkill /PID %PID% /T /F >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [错误] %LABEL% 停止失败，PID=%PID%
    >> "%LOG_FILE%" echo [%date% %time%] [错误] %LABEL% 停止失败，PID=%PID%
    goto :eof
)

echo %LABEL% 已停止，PID=%PID%
>> "%LOG_FILE%" echo [%date% %time%] %LABEL% 已停止，PID=%PID%
del /q "%PIDFILE%" >nul 2>&1
goto :eof
