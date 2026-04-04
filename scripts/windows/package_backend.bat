@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Package Backend Deploy Bundle

echo ================================================
echo   KS Quality Control - Backend Packager
echo ================================================
echo.

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\..") do set "ROOT=%%~fI"

set "SERVER_DIR=%ROOT%\server"
set "RELEASE_DIR=%ROOT%\release"
set "DEV_SITE_PACKAGES=%ROOT%\.venv\Lib\site-packages"
set "WIN7_VENV_CFG=%ROOT%\.venv_win7\pyvenv.cfg"
set "WIN7_PY_HOME="

if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"

where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell was not found.
    goto :fail
)

if not exist "%DEV_SITE_PACKAGES%" (
    echo [ERROR] Missing development site-packages at %DEV_SITE_PACKAGES%
    goto :fail
)

if not exist "%WIN7_VENV_CFG%" (
    echo [ERROR] Missing Win7 venv config at %WIN7_VENV_CFG%
    goto :fail
)

for /f "tokens=3* delims= " %%a in ('findstr /B /C:"home = " "%WIN7_VENV_CFG%"') do if not defined WIN7_PY_HOME set "WIN7_PY_HOME=%%a"
if not defined WIN7_PY_HOME (
    echo [ERROR] Failed to resolve Win7 Python home from %WIN7_VENV_CFG%
    goto :fail
)
set "WIN7_SITE_PACKAGES=%WIN7_PY_HOME%\Lib\site-packages"
if not exist "%WIN7_SITE_PACKAGES%" (
    echo [ERROR] Missing Win7 base site-packages at %WIN7_SITE_PACKAGES%
    goto :fail
)

for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%i"
set "PACKAGE_NAME=ksqc_backend_win7_%TS%"
set "PACKAGE_DIR=%RELEASE_DIR%\%PACKAGE_NAME%"
set "ARCHIVE_PATH=%RELEASE_DIR%\%PACKAGE_NAME%.zip"

if exist "%PACKAGE_DIR%" rd /s /q "%PACKAGE_DIR%"
if exist "%ARCHIVE_PATH%" del /f /q "%ARCHIVE_PATH%"

echo [1/5] Copy backend source...
robocopy "%SERVER_DIR%" "%PACKAGE_DIR%\server" /E /XD "__pycache__" "data" "uploads" "dist" /XF "*.pyc" "*.pyo" >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
    echo [ERROR] robocopy failed with code %RC%.
    goto :fail
)

echo [2/5] Initialize runtime folders...
if not exist "%PACKAGE_DIR%\server\data" mkdir "%PACKAGE_DIR%\server\data"
if not exist "%PACKAGE_DIR%\server\uploads" mkdir "%PACKAGE_DIR%\server\uploads"
> "%PACKAGE_DIR%\server\data\.keep" echo keep
> "%PACKAGE_DIR%\server\uploads\.keep" echo keep
copy /Y "%SERVER_DIR%\deploy\start_server_win7.bat" "%PACKAGE_DIR%\start_server.bat" >nul
copy /Y "%SERVER_DIR%\deploy\stop_server_win7.bat" "%PACKAGE_DIR%\stop_server.bat" >nul

echo [3/5] Bundle offline Python dependencies...
if not exist "%PACKAGE_DIR%\python_deps" mkdir "%PACKAGE_DIR%\python_deps"
call :copy_dep_dir "%DEV_SITE_PACKAGES%\apscheduler" "%PACKAGE_DIR%\python_deps\apscheduler"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\APScheduler-3.10.4.dist-info" "%PACKAGE_DIR%\python_deps\APScheduler-3.10.4.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\blinker" "%PACKAGE_DIR%\python_deps\blinker"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\blinker-1.9.0.dist-info" "%PACKAGE_DIR%\python_deps\blinker-1.9.0.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\click" "%PACKAGE_DIR%\python_deps\click"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\click-8.3.1.dist-info" "%PACKAGE_DIR%\python_deps\click-8.3.1.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\colorama" "%PACKAGE_DIR%\python_deps\colorama"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\colorama-0.4.6.dist-info" "%PACKAGE_DIR%\python_deps\colorama-0.4.6.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\dateutil" "%PACKAGE_DIR%\python_deps\dateutil"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\python_dateutil-2.9.0.post0.dist-info" "%PACKAGE_DIR%\python_deps\python_dateutil-2.9.0.post0.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\docx" "%PACKAGE_DIR%\python_deps\docx"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\python_docx-1.1.0.dist-info" "%PACKAGE_DIR%\python_deps\python_docx-1.1.0.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\et_xmlfile" "%PACKAGE_DIR%\python_deps\et_xmlfile"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\et_xmlfile-2.0.0.dist-info" "%PACKAGE_DIR%\python_deps\et_xmlfile-2.0.0.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\flask" "%PACKAGE_DIR%\python_deps\flask"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\flask-2.3.3.dist-info" "%PACKAGE_DIR%\python_deps\flask-2.3.3.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\flask_cors" "%PACKAGE_DIR%\python_deps\flask_cors"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\Flask_Cors-4.0.0.dist-info" "%PACKAGE_DIR%\python_deps\Flask_Cors-4.0.0.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\flask_jwt_extended" "%PACKAGE_DIR%\python_deps\flask_jwt_extended"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\Flask_JWT_Extended-4.6.0.dist-info" "%PACKAGE_DIR%\python_deps\Flask_JWT_Extended-4.6.0.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\flask_sqlalchemy" "%PACKAGE_DIR%\python_deps\flask_sqlalchemy"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\flask_sqlalchemy-3.1.1.dist-info" "%PACKAGE_DIR%\python_deps\flask_sqlalchemy-3.1.1.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\itsdangerous" "%PACKAGE_DIR%\python_deps\itsdangerous"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\itsdangerous-2.2.0.dist-info" "%PACKAGE_DIR%\python_deps\itsdangerous-2.2.0.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\jinja2" "%PACKAGE_DIR%\python_deps\jinja2"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\jinja2-3.1.6.dist-info" "%PACKAGE_DIR%\python_deps\jinja2-3.1.6.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\jwt" "%PACKAGE_DIR%\python_deps\jwt"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\pyjwt-2.11.0.dist-info" "%PACKAGE_DIR%\python_deps\pyjwt-2.11.0.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\openpyxl" "%PACKAGE_DIR%\python_deps\openpyxl"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\openpyxl-3.1.2.dist-info" "%PACKAGE_DIR%\python_deps\openpyxl-3.1.2.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\pytz" "%PACKAGE_DIR%\python_deps\pytz"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\pytz-2026.1.post1.dist-info" "%PACKAGE_DIR%\python_deps\pytz-2026.1.post1.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_file "%DEV_SITE_PACKAGES%\six.py" "%PACKAGE_DIR%\python_deps\six.py"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\six-1.17.0.dist-info" "%PACKAGE_DIR%\python_deps\six-1.17.0.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\sqlalchemy" "%PACKAGE_DIR%\python_deps\sqlalchemy"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\SQLAlchemy-2.0.25.dist-info" "%PACKAGE_DIR%\python_deps\SQLAlchemy-2.0.25.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_file "%DEV_SITE_PACKAGES%\typing_extensions.py" "%PACKAGE_DIR%\python_deps\typing_extensions.py"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\typing_extensions-4.15.0.dist-info" "%PACKAGE_DIR%\python_deps\typing_extensions-4.15.0.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\tzdata" "%PACKAGE_DIR%\python_deps\tzdata"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\tzdata-2025.3.dist-info" "%PACKAGE_DIR%\python_deps\tzdata-2025.3.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\tzlocal" "%PACKAGE_DIR%\python_deps\tzlocal"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\tzlocal-5.3.1.dist-info" "%PACKAGE_DIR%\python_deps\tzlocal-5.3.1.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\werkzeug" "%PACKAGE_DIR%\python_deps\werkzeug"
if errorlevel 1 goto :fail
call :copy_dep_dir "%DEV_SITE_PACKAGES%\werkzeug-2.3.8.dist-info" "%PACKAGE_DIR%\python_deps\werkzeug-2.3.8.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%WIN7_SITE_PACKAGES%\backports" "%PACKAGE_DIR%\python_deps\backports"
if errorlevel 1 goto :fail
call :copy_dep_dir "%WIN7_SITE_PACKAGES%\backports.zoneinfo-0.2.1.dist-info" "%PACKAGE_DIR%\python_deps\backports.zoneinfo-0.2.1.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%WIN7_SITE_PACKAGES%\greenlet" "%PACKAGE_DIR%\python_deps\greenlet"
if errorlevel 1 goto :fail
call :copy_dep_dir "%WIN7_SITE_PACKAGES%\greenlet-3.1.1.dist-info" "%PACKAGE_DIR%\python_deps\greenlet-3.1.1.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%WIN7_SITE_PACKAGES%\importlib_metadata" "%PACKAGE_DIR%\python_deps\importlib_metadata"
if errorlevel 1 goto :fail
call :copy_dep_dir "%WIN7_SITE_PACKAGES%\importlib_metadata-8.5.0.dist-info" "%PACKAGE_DIR%\python_deps\importlib_metadata-8.5.0.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%WIN7_SITE_PACKAGES%\lxml" "%PACKAGE_DIR%\python_deps\lxml"
if errorlevel 1 goto :fail
call :copy_dep_dir "%WIN7_SITE_PACKAGES%\lxml-6.0.2.dist-info" "%PACKAGE_DIR%\python_deps\lxml-6.0.2.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%WIN7_SITE_PACKAGES%\markupsafe" "%PACKAGE_DIR%\python_deps\markupsafe"
if errorlevel 1 goto :fail
call :copy_dep_dir "%WIN7_SITE_PACKAGES%\MarkupSafe-2.1.5.dist-info" "%PACKAGE_DIR%\python_deps\MarkupSafe-2.1.5.dist-info"
if errorlevel 1 goto :fail
call :copy_dep_dir "%WIN7_SITE_PACKAGES%\zipp" "%PACKAGE_DIR%\python_deps\zipp"
if errorlevel 1 goto :fail
call :copy_dep_dir "%WIN7_SITE_PACKAGES%\zipp-3.20.2.dist-info" "%PACKAGE_DIR%\python_deps\zipp-3.20.2.dist-info"
if errorlevel 1 goto :fail

echo [4/5] Write deployment notes...
> "%PACKAGE_DIR%\README.txt" (
    echo KS Quality Control Backend Deploy Bundle ^(Win7 focused^)
    echo ======================================================
    echo.
    echo 1. Extract this bundle to any folder, for example D:\KsQualityControlServer
    echo 2. On Win7, install Python 3.8.x 64-bit and add it to PATH.
    echo 3. Run start_server.bat
    echo 4. After startup completes, the black console window will close and the backend will keep running in background.
    echo 5. Run stop_server.bat when you need to stop the backend.
    echo 6. The bundle contains offline Python dependencies and can start without internet access.
    echo 7. The service listens on http://localhost:5000
    echo 8. Startup logs are written to .runtime\logs
    echo.
    echo Notes:
    echo - Python 3.7 is NOT supported by the current backend dependency chain.
    echo - Flask 2.3.3 cannot be installed on Python 3.7.
    echo - The preferred path is bundled offline dependencies in python_deps.
    echo - The Win7 startup script first tries system pip to bootstrap the venv, and only falls back to ensurepip if needed.
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

:copy_dep_dir
if not exist "%~1" (
    echo [ERROR] Missing dependency directory: %~1
    exit /b 1
)
robocopy "%~1" "%~2" /E >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
    echo [ERROR] Failed to copy dependency directory: %~1
    exit /b 1
)
exit /b 0

:copy_dep_file
if not exist "%~1" (
    echo [ERROR] Missing dependency file: %~1
    exit /b 1
)
copy /Y "%~1" "%~2" >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy dependency file: %~1
    exit /b 1
)
exit /b 0

:fail
echo.
if not defined NO_PAUSE pause
exit /b 1

:end
if not defined NO_PAUSE pause
