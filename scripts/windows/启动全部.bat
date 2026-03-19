@echo off
chcp 65001 >nul
setlocal EnableExtensions
title 科室质控平台一键启动

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\..") do set "ROOT=%%~fI"
set "RUNTIME_DIR=%ROOT%\.runtime"
if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"
set "LOG_DIR=%RUNTIME_DIR%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%i"
set "LOG_FILE=%LOG_DIR%\start_all_%TS%.log"

echo ================================================
echo   科室质控平台 - 一键后台启动
echo ================================================
echo.
(
echo [%date% %time%] ================================================
echo [%date% %time%]   科室质控平台 - 一键后台启动
echo [%date% %time%] ================================================
echo [%date% %time%].
)>> "%LOG_FILE%"

echo [1/2] 启动服务端...
>> "%LOG_FILE%" echo [%date% %time%] [1/2] 启动服务端...
call "%ROOT%\启动服务器.bat" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 服务端启动失败，已停止后续步骤。日志：%LOG_FILE%
    (
    echo [%date% %time%].
    echo [%date% %time%] [错误] 服务端启动失败，已停止后续步骤。日志：%LOG_FILE%
    )>> "%LOG_FILE%"
    pause
    exit /b 1
)

echo.
echo [2/2] 启动客户端...
(
echo [%date% %time%].
echo [%date% %time%] [2/2] 启动客户端...
)>> "%LOG_FILE%"
timeout /t 2 >nul
call "%ROOT%\启动客户端.bat" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 客户端启动失败。日志：%LOG_FILE%
    (
    echo [%date% %time%].
    echo [%date% %time%] [错误] 客户端启动失败。日志：%LOG_FILE%
    )>> "%LOG_FILE%"
    pause
    exit /b 1
)

echo.
echo 全部组件已处理完成。
echo 如需停止，请运行 退出运行.bat
echo 日志文件：%LOG_FILE%
(
echo [%date% %time%].
echo [%date% %time%] 全部组件已处理完成。
echo [%date% %time%] 如需停止，请运行 退出运行.bat
echo [%date% %time%] 日志文件：%LOG_FILE%
)>> "%LOG_FILE%"
timeout /t 2 >nul
exit /b 0
