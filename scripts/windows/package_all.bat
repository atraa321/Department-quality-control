@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Package Frontend And Backend

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\..") do set "ROOT=%%~fI"
set "NO_PAUSE=1"

call "%SCRIPT_DIR%\package_frontend.bat"
if errorlevel 1 goto :fail

call "%SCRIPT_DIR%\package_backend.bat"
if errorlevel 1 goto :fail

echo.
echo ================================================
echo   Frontend and backend packages are ready
echo   Check the release directory for the latest zip files
echo ================================================
echo.
goto :end

:fail
echo.
echo [ERROR] Packaging failed.
echo.
if not defined NO_PAUSE pause
exit /b 1

:end
if not defined NO_PAUSE pause
