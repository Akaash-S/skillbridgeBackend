@echo off
echo 🚀 Simple Gunicorn Deployment (Windows)
echo =======================================
echo.

REM Check for required files
if not exist "Dockerfile" (
    echo ❌ Dockerfile not found
    pause
    exit /b 1
)

if not exist "docker-compose.yml" (
    echo ❌ docker-compose.yml not found
    pause
    exit /b 1
)

if not exist ".env" (
    echo ❌ .env file not found
    pause
    exit /b 1
)

echo ✅ All required files found
echo.

REM Create directories
echo 📁 Creating directories...
if not exist "logs" mkdir logs
echo ✅ Directories created
echo.

REM Stop existing containers
echo 🛑 Stopping existing containers...
docker compose down --remove-orphans 2>nul
echo ✅ Existing containers stopped
echo.

REM Clean up
echo 🧹 Cleaning up...
docker system prune -f 2>nul
echo ✅ Cleanup completed
echo.

REM Build the application
echo 🏗️ Building simplified application (Gunicorn only)...
docker compose build --no-cache
if %errorlevel% neq 0 (
    echo ❌ Build failed
    pause
    exit /b 1
)
echo ✅ Build completed successfully
echo.

REM Start the application
echo 🚀 Starting application...
docker compose up -d
if %errorlevel% neq 0 (
    echo ❌ Failed to start application
    pause
    exit /b 1
)
echo ✅ Application started
echo.

REM Wait for services to start
echo ⏳ Waiting for services to start...
timeout /t 15 /nobreak >nul
echo.

REM Check container status
echo 📊 Checking container status...
docker compose ps
echo.

REM Test health endpoint
echo 🏥 Testing health endpoint...
timeout /t 5 /nobreak >nul

set HEALTH_PASSED=false

curl --version >nul 2>&1
if %errorlevel% equ 0 (
    curl -f -s http://localhost/health >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ Health check passed on port 80!
        set HEALTH_PASSED=true
    ) else (
        curl -f -s http://localhost:8000/health >nul 2>&1
        if %errorlevel% equ 0 (
            echo ✅ Health check passed on port 8000!
            set HEALTH_PASSED=true
        )
    )
)

if "%HEALTH_PASSED%"=="true" (
    echo.
    echo 🎉 Deployment successful!
    echo =======================
    echo.
    echo 🔗 Your application is available at:
    echo    Local (port 80):     http://localhost
    echo    Local (port 8000):   http://localhost:8000
    echo    Health check:        http://localhost:8000/health
    echo.
    echo 📋 Architecture:
    echo    ✅ Direct Gunicorn deployment (no Nginx)
    echo    ✅ Port 8000 mapped to port 80
    echo    ✅ Simplified, reliable setup
    echo.
    echo 📋 Useful commands:
    echo    View logs:    docker compose logs -f
    echo    Restart:      docker compose restart
    echo    Stop:         docker compose down
    echo    Status:       docker compose ps
    echo.
) else (
    echo ⚠️ Health check failed. Checking logs...
    echo.
    echo 📋 Container logs:
    docker compose logs --tail=30
    echo.
    echo 🔧 Debug commands:
    echo    docker compose logs -f
    echo    docker compose exec skillbridge ps aux
    echo    docker compose exec skillbridge curl http://localhost:8000/health
)

echo ✅ Deployment script completed!
pause