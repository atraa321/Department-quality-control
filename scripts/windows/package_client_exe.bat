@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Package Native Client EXE

echo ================================================
echo   KS Quality Control - Native Client Packager
echo ================================================
echo.

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\..") do set "ROOT=%%~fI"

set "CLIENT_DIR=%ROOT%\client"
set "RELEASE_DIR=%ROOT%\release"
set "BUILD_ROOT=d:\pyinstaller_client_exe"
set "PYTHON38=D:\python38\python.exe"
set "VENV_HOST_PYTHON=%ROOT%\.venv_win7\Scripts\python.exe"
set "UCRT_REDIST_DIR=C:\Program Files (x86)\Windows Kits\10\Redist\ucrt\DLLs\x64"

if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"

if exist "%PYTHON38%" (
    set "BOOTSTRAP_PYTHON=%PYTHON38%"
) else (
    set "BOOTSTRAP_PYTHON=python"
)

if exist "%VENV_HOST_PYTHON%" (
    set "HOST_PYTHON=%VENV_HOST_PYTHON%"
) else (
    set "HOST_PYTHON=python"
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

where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell was not found.
    goto :fail
)

where tar >nul 2>&1
if errorlevel 1 (
    echo [ERROR] tar.exe was not found.
    goto :fail
)

for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%i"
set "PACKAGE_NAME=ksqc_client_exe_win7_%TS%"
set "PACKAGE_DIR=%RELEASE_DIR%\%PACKAGE_NAME%"
set "ARCHIVE_PATH=%RELEASE_DIR%\%PACKAGE_NAME%.zip"
set "DIST_NAME=KsQcClient"

if exist "%BUILD_ROOT%" rd /s /q "%BUILD_ROOT%"
mkdir "%BUILD_ROOT%"
mkdir "%BUILD_ROOT%\src"
mkdir "%BUILD_ROOT%\wheelhouse"

if exist "%PACKAGE_DIR%" rd /s /q "%PACKAGE_DIR%"
if exist "%ARCHIVE_PATH%" del /f /q "%ARCHIVE_PATH%"

echo [1/8] Prepare ASCII build workspace...
robocopy "%CLIENT_DIR%" "%BUILD_ROOT%\src" /E /XD "__pycache__" "build" "dist" /XF "*.pyc" "*.pyo" >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
    echo [ERROR] robocopy failed with code %RC%.
    goto :fail
)

echo [2/8] Create Python 3.8 build environment...
"%BOOTSTRAP_PYTHON%" -m venv "%BUILD_ROOT%\venv"
if errorlevel 1 (
    echo [ERROR] failed to create virtual environment.
    goto :fail
)
set "PYTHON=%BUILD_ROOT%\venv\Scripts\python.exe"

set http_proxy=
set https_proxy=
set HTTP_PROXY=
set HTTPS_PROXY=
set all_proxy=
set ALL_PROXY=

echo [3/8] Download offline wheelhouse...
"%HOST_PYTHON%" -m pip download -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --dest "%BUILD_ROOT%\wheelhouse" --only-binary=:all: --platform win_amd64 --python-version 38 --implementation cp PyQt5==5.15.7 PyQt5-Qt5==5.15.2 PyQt5-sip==12.11.0 requests==2.31.0 pyinstaller==4.10 setuptools==68.0.0 importlib-metadata==6.7.0 typing-extensions==4.7.1
if errorlevel 1 (
    echo [ERROR] wheel download failed.
    goto :fail
)

echo [4/8] Install packaging dependencies...
"%PYTHON%" -m pip install -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [ERROR] pip bootstrap failed.
    goto :fail
)
"%PYTHON%" -m pip install --no-index --find-links "%BUILD_ROOT%\wheelhouse" setuptools==68.0.0 importlib-metadata==6.7.0 typing-extensions==4.7.1 PyQt5==5.15.7 PyQt5-Qt5==5.15.2 PyQt5-sip==12.11.0 requests==2.31.0 pyinstaller==4.10
if errorlevel 1 (
    echo [ERROR] dependency installation failed.
    goto :fail
)

echo [5/8] Build native client EXE...
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
    --hidden-import PyQt5.QtNetwork ^
    --hidden-import PyQt5.QtCore ^
    --hidden-import PyQt5.QtGui ^
    --hidden-import PyQt5.QtWidgets ^
    --collect-submodules requests ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module scipy ^
    --exclude-module tkinter ^
    main.py
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    goto :fail
)

echo [6/8] Normalize Win7 runtime DLLs...
if exist "%UCRT_REDIST_DIR%\ucrtbase.dll" (
    robocopy "%UCRT_REDIST_DIR%" "%BUILD_ROOT%\dist\%DIST_NAME%" api-ms-win-*.dll ucrtbase.dll /NFL /NDL /NJH /NJS /NC /NS /NP >nul
    set "RC=%ERRORLEVEL%"
    if %RC% GEQ 8 (
        echo [ERROR] failed to overlay Windows SDK UCRT runtime files.
        goto :fail
    )
) else (
    if exist "%BUILD_ROOT%\dist\%DIST_NAME%\ucrtbase.dll" del /q "%BUILD_ROOT%\dist\%DIST_NAME%\ucrtbase.dll"
    if exist "%BUILD_ROOT%\dist\%DIST_NAME%\api-ms-win-crt-conio-l1-1-0.dll" del /q "%BUILD_ROOT%\dist\%DIST_NAME%\api-ms-win-crt-*.dll"
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
    echo KS Quality Control Native Client Bundle ^(Win7-focused^)
    echo ======================================================
    echo.
    echo 1. Extract the whole package and keep the %DIST_NAME% folder structure unchanged.
    echo 2. Run %DIST_NAME%\%DIST_NAME%.exe.
    echo 3. Default server URL is http://localhost:5000 and can be changed in client settings.
    echo 4. This EXE is packaged with Python 3.8 tooling and a Win7-safe UCRT runtime overlay.
    echo 5. Browser fallback remains available from the client header, tray and overlay menus.
    echo 6. On Windows 7, install Service Pack 1, KB2533623 and Microsoft Visual C++ 2015-2022 Redistributable ^(x64^) first.
    echo 7. If the EXE reports missing api-ms-win-core-* or api-ms-win-crt-* DLLs, fix Windows prerequisites instead of downloading random DLL files.
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

echo.
echo ================================================
echo   Native client package complete
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
