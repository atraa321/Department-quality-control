@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Package Frontend Static Bundle

echo ================================================
echo   KS Quality Control - Frontend Packager
echo ================================================
echo.

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\..") do set "ROOT=%%~fI"

set "FRONTEND_DIR=%ROOT%\frontend"
set "RELEASE_DIR=%ROOT%\release"

if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found.
    goto :fail
)

where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell was not found.
    goto :fail
)

for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%i"
set "PACKAGE_NAME=ksqc_frontend_win7_%TS%"
set "PACKAGE_DIR=%RELEASE_DIR%\%PACKAGE_NAME%"
set "ARCHIVE_PATH=%RELEASE_DIR%\%PACKAGE_NAME%.zip"

if exist "%PACKAGE_DIR%" rd /s /q "%PACKAGE_DIR%"
if exist "%ARCHIVE_PATH%" del /f /q "%ARCHIVE_PATH%"

echo [1/4] Build frontend...
pushd "%FRONTEND_DIR%"
if not exist "node_modules" (
    call npm install
    if errorlevel 1 (
        popd
        echo [ERROR] npm install failed.
        goto :fail
    )
)
call npm run build
if errorlevel 1 (
    popd
    echo [ERROR] frontend build failed.
    goto :fail
)
popd

if not exist "%FRONTEND_DIR%\dist\index.html" (
    echo [ERROR] dist\index.html was not generated.
    goto :fail
)

echo [2/4] Copy static assets...
robocopy "%FRONTEND_DIR%\dist" "%PACKAGE_DIR%\frontend\dist" /E >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
    echo [ERROR] robocopy failed with code %RC%.
    goto :fail
)

echo [3/4] Write deployment notes...
> "%PACKAGE_DIR%\README.txt" (
    echo KS Quality Control Frontend Static Bundle ^(Win7-friendly build^)
    echo ============================================================
    echo.
    echo 1. This bundle is already built on a modern Node.js environment.
    echo 2. Do not build on Win7 if you can avoid it. Use this archive directly.
    echo 3. Extract to a directory that contains frontend\dist\index.html.
    echo 4. For Flask integrated serving, place frontend next to the backend package root.
    echo 5. If frontend is stored elsewhere, set KSQC_STATIC_DIR to the dist path.
    echo 6. This build includes a legacy compatibility layer for older Chromium-based browsers on Win7.
    echo 7. IE11 is still not supported. Use Chrome, 360 Extreme mode, Edge Chromium or another Chromium-based browser.
)

echo [4/4] Create zip archive...
powershell -NoProfile -Command "Compress-Archive -Path '%PACKAGE_DIR%\*' -DestinationPath '%ARCHIVE_PATH%' -Force"
if errorlevel 1 (
    echo [ERROR] archive creation failed.
    goto :fail
)

echo.
echo ================================================
echo   Frontend package complete
echo   Folder : %PACKAGE_DIR%
echo   Zip    : %ARCHIVE_PATH%
echo ================================================
echo.
goto :end

:fail
echo.
if not defined NO_PAUSE pause
exit /b 1

:end
if not defined NO_PAUSE pause
