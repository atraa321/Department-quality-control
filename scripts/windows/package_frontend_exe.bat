@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Package Frontend EXE

echo ================================================
echo   KS Quality Control - Frontend EXE Packager
echo ================================================
echo.

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\..") do set "ROOT=%%~fI"

set "FRONTEND_DIR=%ROOT%\frontend"
set "LAUNCHER_DIR=%ROOT%\frontend_launcher"
set "RELEASE_DIR=%ROOT%\release"
set "BUILD_ROOT=d:\pyinstaller_frontend_exe"
set "PYTHON37=D:\python37\python.exe"
set "VENV_HOST_PYTHON=%ROOT%\.venv\Scripts\python.exe"

if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"

if exist "%PYTHON37%" (
    set "BOOTSTRAP_PYTHON=%PYTHON37%"
) else (
    set "BOOTSTRAP_PYTHON=python"
)

if exist "%VENV_HOST_PYTHON%" (
    set "HOST_PYTHON=%VENV_HOST_PYTHON%"
) else (
    set "HOST_PYTHON=python"
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found.
    goto :fail
)

where tar >nul 2>&1
if errorlevel 1 (
    echo [ERROR] tar.exe was not found.
    goto :fail
)

if /I "%BOOTSTRAP_PYTHON%"=="python" (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python was not found.
        goto :fail
    )
)

if /I "%HOST_PYTHON%"=="python" (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Host Python was not found.
        goto :fail
    )
)

for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%i"
set "PACKAGE_NAME=ksqc_frontend_exe_win7_%TS%"
set "PACKAGE_DIR=%RELEASE_DIR%\%PACKAGE_NAME%"
set "ARCHIVE_PATH=%RELEASE_DIR%\%PACKAGE_NAME%.zip"
set "DIST_NAME=KsQcFrontendLauncher"

if exist "%BUILD_ROOT%" rd /s /q "%BUILD_ROOT%"
mkdir "%BUILD_ROOT%"
mkdir "%BUILD_ROOT%\src"
mkdir "%BUILD_ROOT%\frontend_dist"
mkdir "%BUILD_ROOT%\wheelhouse"

if exist "%PACKAGE_DIR%" rd /s /q "%PACKAGE_DIR%"
if exist "%ARCHIVE_PATH%" del /f /q "%ARCHIVE_PATH%"

echo [1/8] Build frontend...
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

echo [2/8] Prepare ASCII build workspace...
copy /Y "%LAUNCHER_DIR%\app.py" "%BUILD_ROOT%\src\app.py" >nul
robocopy "%FRONTEND_DIR%\dist" "%BUILD_ROOT%\frontend_dist" /E >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
    echo [ERROR] robocopy failed with code %RC%.
    goto :fail
)

echo [3/8] Create Python 3.7 build environment...
"%BOOTSTRAP_PYTHON%" -m venv "%BUILD_ROOT%\venv"
if errorlevel 1 (
    echo [ERROR] failed to create virtual environment.
    goto :fail
)
set "PYTHON=%BUILD_ROOT%\venv\Scripts\python.exe"

echo [4/8] Download PyInstaller wheels with host Python...
"%HOST_PYTHON%" -m pip download --dest "%BUILD_ROOT%\wheelhouse" --only-binary=:all: --platform win_amd64 --python-version 37 --implementation cp pyinstaller==5.13.2 importlib-metadata==6.7.0 typing-extensions==4.7.1 setuptools==68.0.0
if errorlevel 1 (
    echo [ERROR] wheel download failed.
    goto :fail
)

echo [5/8] Install PyInstaller from offline wheelhouse...
"%PYTHON%" -m pip install --no-index --find-links "%BUILD_ROOT%\wheelhouse" setuptools==68.0.0 importlib-metadata==6.7.0 typing-extensions==4.7.1 pyinstaller==5.13.2
if errorlevel 1 (
    echo [ERROR] offline PyInstaller install failed.
    goto :fail
)

echo [6/8] Build frontend launcher EXE...
cd /d "%BUILD_ROOT%\src"
"%PYTHON%" -m PyInstaller ^
    --name "%DIST_NAME%" ^
    --onedir ^
    --windowed ^
    --clean ^
    --noconfirm ^
    --distpath "%BUILD_ROOT%\dist" ^
    --workpath "%BUILD_ROOT%\work" ^
    --specpath "%BUILD_ROOT%" ^
    --add-data "%BUILD_ROOT%\frontend_dist;frontend_dist" ^
    app.py
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    goto :fail
)

echo [7/8] Copy release files...
mkdir "%PACKAGE_DIR%"
robocopy "%BUILD_ROOT%\dist\%DIST_NAME%" "%PACKAGE_DIR%\%DIST_NAME%" /E >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
    echo [ERROR] release copy failed with code %RC%.
    goto :fail
)

> "%PACKAGE_DIR%\README.txt" (
    echo KS Quality Control Frontend EXE Bundle ^(Win7-friendly^)
    echo =====================================================
    echo.
    echo 1. Run %DIST_NAME%\%DIST_NAME%.exe.
    echo 2. Default backend URL is http://127.0.0.1:5000. Change it in the launcher window if needed.
    echo 3. API requests are proxied by the EXE to the backend URL above.
    echo 4. IE11 is not supported. On Win7, point the launcher to Chrome or another Chromium-based browser if the default browser is too old.
    echo 5. This bundle is built with Python 3.7 tooling for better Win7 deployment compatibility.
)

echo [8/8] Create zip archive...
pushd "%RELEASE_DIR%"
tar -a -cf "%ARCHIVE_PATH%" "%PACKAGE_NAME%"
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" (
    echo [ERROR] archive creation failed with code %RC%.
    goto :fail
)

if not exist "%ARCHIVE_PATH%" (
    echo [ERROR] archive was not created.
    goto :fail
)

echo.
echo ================================================
echo   Frontend EXE package complete
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
