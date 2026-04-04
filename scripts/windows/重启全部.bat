@echo off
chcp 65001 >nul
setlocal EnableExtensions
title 科室质控平台重启

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
set "LOG_FILE=%LOG_DIR%\restart_all_%TS%.log"

echo ================================================
echo   科室质控平台 - 重启全部组件
echo ================================================
echo.
(
echo [%date% %time%] ================================================
echo [%date% %time%]   科室质控平台 - 重启全部组件
echo [%date% %time%] ================================================
echo [%date% %time%].
)>> "%LOG_FILE%"

echo [1/2] 停止现有后台进程...
>> "%LOG_FILE%" echo [%date% %time%] [1/2] 停止现有后台进程...
call "%ROOT%\退出运行.bat" --nopause >> "%LOG_FILE%" 2>&1

echo [2/2] 重新启动全部组件...
>> "%LOG_FILE%" echo [%date% %time%] [2/2] 重新启动全部组件...
call "%ROOT%\启动全部.bat" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [错误] 重启过程中启动失败，请查看日志：%LOG_FILE%
    >> "%LOG_FILE%" echo [%date% %time%] [错误] 重启过程中启动失败，请查看日志：%LOG_FILE%
    if not defined NO_PAUSE pause
    exit /b 1
)

echo 重启完成。
echo 日志文件：%LOG_FILE%
(
echo [%date% %time%] 重启完成。
echo [%date% %time%] 日志文件：%LOG_FILE%
)>> "%LOG_FILE%"
if not defined NO_PAUSE ping 127.0.0.1 -n 3 >nul
exit /b 0
