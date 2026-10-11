@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  Honeypots with Attack Analytics - Starting Platform
echo ============================================================
echo.

where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not on PATH. Run setup.bat first.
    pause
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running. Please start it and try again.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [ERROR] .env file not found. Please run setup.bat first.
    pause
    exit /b 1
)

echo [INFO] Starting all services in the background...
docker compose up -d
if errorlevel 1 (
    echo [ERROR] Failed to start services. Run "docker compose logs" for details.
    pause
    exit /b 1
)

echo.
echo [INFO] Waiting for the backend API to become healthy...

set RETRIES=0
:WAITLOOP
set /a RETRIES+=1
curl -s -o nul -w "%%{http_code}" http://localhost:8000/api/v1/health > "%TEMP%\hp_status.txt" 2>nul
set /p STATUS=<"%TEMP%\hp_status.txt"
if "%STATUS%"=="200" goto READY
if %RETRIES% GEQ 30 goto TIMEOUT
timeout /t 2 >nul
goto WAITLOOP

:TIMEOUT
echo [WARN] Backend did not report healthy in time. Check logs with:
echo        docker compose logs backend
goto OPEN

:READY
echo [OK] Backend is up.

:OPEN
echo.
echo ============================================================
echo  Platform is running:
echo    Frontend (via Nginx) : http://localhost
echo    Backend API docs     : http://localhost:8000/api/v1/docs
echo    Cowrie SSH honeypot   : localhost:2222
echo.
echo  Default login (change after first sign-in):
echo    username: admin
echo    password: see DEFAULT_ADMIN_PASSWORD in .env
echo.
echo  To stop the platform: docker compose down
echo  To view logs:         docker compose logs -f
echo ============================================================

start "" http://localhost

pause
