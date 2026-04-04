@echo off
chcp 65001 >nul
setlocal EnableExtensions

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

call "%ROOT%\scripts\windows\启动客户端.bat" %*
exit /b %errorlevel%
