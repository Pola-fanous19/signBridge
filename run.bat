@echo off
REM ============================================================
REM  SignBridge v4 - One-Click Launcher (Windows)
REM ============================================================

setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

echo.
echo =========================================================
echo   SignBridge v4 - One-Click Launcher
echo =========================================================
echo   Working folder: %CD%
echo.

REM --- 1. Detect Python -----------------------------------------------
set "PYCMD="

py -3.13 --version >nul 2>&1
if not errorlevel 1 (
    set "PYCMD=py -3.13"
    goto :python_found
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYCMD=python"
    goto :python_found
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYCMD=py -3"
    goto :python_found
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYCMD=python3"
    goto :python_found
)

echo [ERROR] Python 3.9+ was not found on PATH.
echo         Install from https://www.python.org/downloads/
echo         During install, check "Add python.exe to PATH".
echo.
pause
exit /b 1

:python_found
echo [ok] Python found: !PYCMD!
!PYCMD! --version
echo.

REM --- 2. Detect Node -------------------------------------------------
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js was not found on PATH.
    echo         Install Node 18+ from https://nodejs.org/
    echo.
    pause
    exit /b 1
)
echo [ok] Node found:
node --version
echo [ok] npm found:
cmd /c npm --version
echo.

REM --- 3. Backend setup ----------------------------------------------
echo [1/4] Setting up backend (Python virtualenv + pip install)...
if not exist "backend" (
    echo [ERROR] "backend" folder is missing next to run.bat
    pause
    exit /b 1
)

pushd backend

if not exist ".venv\Scripts\python.exe" (
    echo       Creating Python virtual environment .venv...
    !PYCMD! -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtualenv.
        popd
        pause
        exit /b 1
    )
)

set "VENV_PY=%CD%\.venv\Scripts\python.exe"

if not exist "!VENV_PY!" (
    echo [ERROR] Virtualenv python was not created at:
    echo         !VENV_PY!
    popd
    pause
    exit /b 1
)

echo       Upgrading pip...
"!VENV_PY!" -m pip install --quiet --upgrade pip
if errorlevel 1 (
    echo [WARN] pip upgrade failed - continuing.
)

echo       Installing backend dependencies (first run only, ~1 min)...
set PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
"!VENV_PY!" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. See error above.
    popd
    pause
    exit /b 1
)
echo [ok] Backend dependencies installed.
popd
echo.

REM --- 4. Frontend setup ---------------------------------------------
echo [2/4] Setting up frontend (npm install)...
if not exist "frontend" (
    echo [ERROR] "frontend" folder is missing next to run.bat
    pause
    exit /b 1
)

pushd frontend
if not exist "node_modules" (
    echo       Running npm install, first run only, 1-2 minutes...
    cmd /c npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed. See error above.
        popd
        pause
        exit /b 1
    )
) else (
    echo [ok] node_modules already present, skipping npm install.
)
popd
echo.

REM --- 5. Launch backend + frontend ----------------------------------
echo [3/4] Starting backend on http://localhost:8000 ...
(
    echo @echo off
    echo cd /d "%~dp0backend"
    echo "%~dp0backend\.venv\Scripts\python.exe" -m flask --app app.main run --host 0.0.0.0 --port 8000
) > "%~dp0_start_backend.bat"
start "SignBridge Backend" cmd /k "%~dp0_start_backend.bat"

echo       Waiting a few seconds for backend to boot...
timeout /t 5 /nobreak >nul

echo [4/4] Starting frontend on http://localhost:5173 ...
(
    echo @echo off
    echo cd /d "%~dp0frontend"
    echo call npm run dev
) > "%~dp0_start_frontend.bat"
start "SignBridge Frontend" cmd /k "%~dp0_start_frontend.bat"

echo       Waiting for Vite to compile...
timeout /t 6 /nobreak >nul

start "" "http://localhost:5173"

echo.
echo =========================================================
echo   SignBridge v4 is running!
echo   - Backend:  http://localhost:8000
echo   - Frontend: http://localhost:5173   (opened in browser)
echo.
echo   Two console windows have opened:
echo     * "SignBridge Backend"
echo     * "SignBridge Frontend"
echo   Keep them open while using the app.
echo   To stop: close those windows, or run stop.bat.
echo =========================================================
echo.
pause
endlocal
