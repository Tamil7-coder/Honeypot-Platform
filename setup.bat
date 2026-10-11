@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  Honeypots with Attack Analytics - First-Time Setup
echo ============================================================
echo.

REM --- 1. Docker Desktop / Engine availability -------------------------
where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker was not found on PATH. Install Docker Desktop from
    echo         https://www.docker.com/products/docker-desktop and re-run this script.
    pause
    exit /b 1
)

echo [INFO] Checking that Docker Desktop is running...
docker info >nul 2>nul
if errorlevel 1 (
    echo [WARN] Docker does not appear to be running yet. Attempting to start Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe" 2>nul

    set RETRIES=0
    :DOCKER_WAIT
    set /a RETRIES+=1
    timeout /t 3 >nul
    docker info >nul 2>nul
    if not errorlevel 1 goto DOCKER_READY
    if !RETRIES! GEQ 20 (
        echo [ERROR] Docker Desktop did not start within the expected time.
        echo         Please start Docker Desktop manually and re-run setup.bat.
        pause
        exit /b 1
    )
    goto DOCKER_WAIT
)

:DOCKER_READY
echo [OK] Docker is running.
echo.

REM --- 2. Environment file ----------------------------------------------
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] No .env found -- creating one from .env.example.
        copy /y ".env.example" ".env" >nul
        echo [WARN] Review .env and set a real SECRET_KEY / admin password before production use.
    ) else (
        echo [ERROR] Neither .env nor .env.example was found. Aborting.
        pause
        exit /b 1
    )
) else (
    echo [OK] .env already present.
)
echo.

REM --- 3. Build and start all containers ---------------------------------
echo [INFO] Building and starting all containers (this can take a few minutes on first run)...
docker compose up -d --build
if errorlevel 1 (
    echo [ERROR] docker compose up failed. Run "docker compose logs" for details.
    pause
    exit /b 1
)
echo [OK] All containers built and started.
echo.

REM --- 4. Wait for backend health before verifying -----------------------
echo [INFO] Waiting for the backend API to become healthy...
set RETRIES=0
:WAITLOOP
set /a RETRIES+=1
curl -s -o nul -w "%%{http_code}" http://localhost:8000/api/v1/health > "%TEMP%\hp_status.txt" 2>nul
set /p STATUS=<"%TEMP%\hp_status.txt"
if "%STATUS%"=="200" goto BACKEND_READY
if %RETRIES% GEQ 30 (
    echo [WARN] Backend did not report healthy in time. Continuing anyway --
    echo        check "docker compose logs backend" if verification below fails.
    goto RUN_VERIFY
)
timeout /t 2 >nul
goto WAITLOOP

:BACKEND_READY
echo [OK] Backend is healthy.
echo.

REM --- 5. Run the attack simulation / pipeline verification script -------
:RUN_VERIFY
echo ============================================================
echo  Running honeypot pipeline verification (verify_attacks.ps1)
echo ============================================================
where pwsh >nul 2>nul
if not errorlevel 1 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify_attacks.ps1"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify_attacks.ps1"
)

echo.
echo ============================================================
echo  Setup complete.
echo    Frontend (via Nginx) : http://localhost
echo    Backend API docs     : http://localhost:8000/api/v1/docs
echo    Default login        : admin@honeypot-platform.com / see .env (DEFAULT_ADMIN_PASSWORD)
echo    To start the platform later, use run.bat
echo ============================================================
pause
