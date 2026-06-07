@echo off
echo ========================================
echo   mercari one-click build (PyInstaller)
echo ========================================

rem ===== Version (edit this on each release) =====
set VERSION=v1.0.0

rem ===== Bundle OCR (easyocr/torch, ~2GB, slower start). 0=no 1=yes =====
set BUNDLE_OCR=0

set ROOT=%~dp0
set RELEASE=%ROOT%Releases\%VERSION%

rem ===== Activate conda env mercari =====
echo.
echo [0/6] Activating conda env mercari ...
call conda activate mercari
if %errorlevel% neq 0 (
    echo ERROR: failed to activate conda env mercari
    pause
    exit /b 1
)

rem ===== Ensure pyinstaller is available =====
where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo pyinstaller not found, installing...
    pip install pyinstaller
)

rem ===== Prepare release directory =====
echo.
echo [1/6] Cleaning and creating release dir %RELEASE% ...
if exist "%RELEASE%" rmdir /s /q "%RELEASE%"
mkdir "%RELEASE%"
if exist "%ROOT%build" rmdir /s /q "%ROOT%build"

rem ===== Build frontend =====
echo.
echo [2/6] Building frontend webside ...
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: npm not found, please install Node.js: https://nodejs.org/
    pause
    exit /b 1
)
pushd "%ROOT%webside"
if not exist "node_modules" (
    echo Installing frontend deps...
    call npm install
    if %errorlevel% neq 0 ( echo ERROR: npm install failed & popd & pause & exit /b 1 )
)
call npm run build
if %errorlevel% neq 0 ( echo ERROR: frontend build failed & popd & pause & exit /b 1 )
popd
if not exist "%ROOT%webside\dist\index.html" (
    echo ERROR: webside\dist\index.html not found, frontend build may have failed
    pause
    exit /b 1
)

rem ===== Build main program mercari.exe =====
echo.
echo [3/6] Building mercari.exe ...
pyinstaller --clean --noconfirm "%ROOT%mercari.spec" ^
    --distpath "%RELEASE%" --workpath "%ROOT%build\mercari"
if %errorlevel% neq 0 (
    echo ERROR: mercari.exe build failed
    pause
    exit /b 1
)

rem ===== Build mitmdump.exe into Scripts\ (used by MITM subprocess) =====
echo.
echo [4/6] Building Scripts\mitmdump.exe ...
pyinstaller --clean --noconfirm "%ROOT%mitmdump.spec" ^
    --distpath "%RELEASE%\Scripts" --workpath "%ROOT%build\mitmdump"
if %errorlevel% neq 0 (
    echo WARNING: mitmdump.exe build failed -- MITM capture will be unavailable in this package, other features unaffected.
)

rem ===== Copy frontend dist next to exe: webside\dist =====
echo.
echo [5/6] Copying frontend webside\dist ...
mkdir "%RELEASE%\webside\dist"
xcopy "%ROOT%webside\dist" "%RELEASE%\webside\dist\" /E /I /H /Y /Q
if %errorlevel% neq 0 (
    echo ERROR: copying webside\dist failed
    pause
    exit /b 1
)

rem ===== Generate start script =====
echo.
echo [6/6] Generating start script and ZIP ...
(
    echo @echo off
    echo cd /d %%~dp0
    echo echo mercari starting... open http://localhost:9601 in your browser
    echo start "" http://localhost:9601
    echo mercari.exe
    echo pause
) > "%RELEASE%\start_mercari.bat"

rem Note: Playwright uses the system-installed Microsoft Edge (channel=msedge); target machine must have Edge (bundled with Win11).

rem ===== Make ZIP =====
set ZIP_FILE=%ROOT%Releases\mercari_%VERSION%.zip
if exist "%ZIP_FILE%" del /q "%ZIP_FILE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Compress-Archive -Path '%RELEASE%\*' -DestinationPath '%ZIP_FILE%' -CompressionLevel Optimal -Force"

rem ===== Clean build intermediates =====
if exist "%ROOT%build" rmdir /s /q "%ROOT%build"

echo.
echo ========================================
echo   Build complete! Output dir: %RELEASE%
echo ========================================
dir /b "%RELEASE%"
echo ----------------------------------------
echo   Double-click to run: %RELEASE%\start_mercari.bat
echo   Or run mercari.exe directly, then open http://localhost:9601
echo   ZIP: %ZIP_FILE%
echo ========================================
pause
