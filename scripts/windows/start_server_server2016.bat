@echo off
chcp 65001 >nul
setlocal EnableExtensions
title KSQC Server 2016 Launcher

set "NO_PAUSE="
if /I "%~1"=="--nopause" set "NO_PAUSE=1"

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\..") do set "ROOT=%%~fI"

call "%ROOT%\server\deploy\start_server_server2016.bat" %*
exit /b %errorlevel%
