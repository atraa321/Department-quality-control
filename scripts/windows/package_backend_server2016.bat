@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Package Backend Deploy Bundle For Server 2016

echo ================================================
echo   KS Quality Control - Backend Packager
echo   Target: Windows Server 2016
echo ================================================
echo.

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\..") do set "ROOT=%%~fI"

set "SERVER_DIR=%ROOT%\server"
set "RELEASE_DIR=%ROOT%\release"
set "HOST_PYTHON=%ROOT%\.venv\Scripts\python.exe"

if not exist "%HOST_PYTHON%" set "HOST_PYTHON=python"

if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"

where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell was not found.
    goto :fail
)

if /I "%HOST_PYTHON%"=="python" (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python was not found.
        goto :fail
    )
)

for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%i"
set "PACKAGE_NAME=ksqc_backend_server2016_%TS%"
set "PACKAGE_DIR=%RELEASE_DIR%\%PACKAGE_NAME%"
set "ARCHIVE_PATH=%RELEASE_DIR%\%PACKAGE_NAME%.zip"

if exist "%PACKAGE_DIR%" rd /s /q "%PACKAGE_DIR%"
if exist "%ARCHIVE_PATH%" del /f /q "%ARCHIVE_PATH%"

echo [1/4] Copy backend source...
robocopy "%SERVER_DIR%" "%PACKAGE_DIR%\server" /E /XD "__pycache__" "data" "uploads" "dist" /XF "*.pyc" "*.pyo" >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
    echo [ERROR] robocopy failed with code %RC%.
    goto :fail
)

echo [2/4] Initialize runtime folders...
if not exist "%PACKAGE_DIR%\server\data" mkdir "%PACKAGE_DIR%\server\data"
if not exist "%PACKAGE_DIR%\server\uploads" mkdir "%PACKAGE_DIR%\server\uploads"
> "%PACKAGE_DIR%\server\data\.keep" echo keep
> "%PACKAGE_DIR%\server\uploads\.keep" echo keep
copy /Y "%SERVER_DIR%\deploy\start_server_server2016.bat" "%PACKAGE_DIR%\start_server.bat" >nul
copy /Y "%SERVER_DIR%\deploy\stop_server_server2016.bat" "%PACKAGE_DIR%\stop_server.bat" >nul

echo [3/5] Download offline wheelhouse...
mkdir "%PACKAGE_DIR%\wheelhouse" >nul 2>&1
"%HOST_PYTHON%" -m pip download --dest "%PACKAGE_DIR%\wheelhouse" --only-binary=:all: "pip==25.0.1" "setuptools==69.5.1" "wheel==0.42.0" -r "%SERVER_DIR%\requirements.txt"
if errorlevel 1 (
    echo [ERROR] Failed to download offline wheelhouse.
    goto :fail
)

echo [4/5] Write deployment notes...
> "%PACKAGE_DIR%\README.txt" (
    echo KS Quality Control Backend Deploy Bundle ^(Windows Server 2016^)
    echo ==============================================================
    echo.
    echo 1. Extract this bundle to any folder, for example D:\KsQualityControlServer
    echo 2. Install Python 3.12.x ^(64-bit recommended^) and add it to PATH.
    echo 3. Run start_server.bat
    echo 4. Run stop_server.bat when you need to stop the backend.
    echo 5. The first start creates .venv and installs runtime dependencies automatically from the bundled wheelhouse.
    echo 6. The service listens on http://localhost:5000
    echo 7. Startup logs are written to .runtime\logs
    echo.
    echo Notes:
    echo - This package is dedicated to Windows Server 2016 and is pinned to Python 3.12.x.
    echo - The package includes an offline wheelhouse, so the target server does not need direct access to pypi.org for normal startup.
    echo - If an old .venv points to a missing Python path, the startup script will recreate it automatically.
    echo - To enable browser fallback pages, extract the frontend bundle next to this package root as frontend\dist
    echo - You may also set KSQC_STATIC_DIR to a custom dist path.
)

echo [5/5] Create zip archive...
powershell -NoProfile -Command "Compress-Archive -Path '%PACKAGE_DIR%\*' -DestinationPath '%ARCHIVE_PATH%' -Force"
if errorlevel 1 (
    echo [ERROR] archive creation failed.
    goto :fail
)

echo.
echo ================================================
echo   Backend package complete
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
