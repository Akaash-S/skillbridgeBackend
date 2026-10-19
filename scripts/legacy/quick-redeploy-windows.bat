@echo off
echo 🔧 Quick Redeploy - Fixed Dockerfile (Windows)
echo ===============================================
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

echo ✅ Required files found
echo.

REM Stop existing containers
echo 🛑 Stopping existing containers...
docker compose down --remove-orphans 2>nul
echo ✅ Containers stopped
echo.

REM Clean Docker cache
echo 🧹 Cleaning Docker cache...
docker system prune -f 2>nul
echo ✅ Cache cleaned
echo.

REM Build with fixed Dockerfile
echo 🏗️ Building with fixed Dockerfile (no Redis, fixed configs)...
docker compose build --no-cache --progress=plain
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

REM Show recent logs
echo 📋 Recent logs:
docker compose logs --tail=20
echo.

REM Test health endpoint
echo 🏥 Testing health endpoint...
timeout /t 5 /nobreak >nul

curl --version >nul 2>&1
if %errorlevel% equ 0 (
    curl -f -s http://localhost/health >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ Health check passed!
        echo.
        echo 🎉 Redeploy successful!
        echo =====================
        echo.
        echo 🔗 Your application is available at:
        echo    Local:    http://localhost
        echo    Health:   http://localhost/health
        echo.
        echo 📋 Key fixes applied:
        echo    ✅ Removed Redis (not needed)
        echo    ✅ Fixed Nginx configuration
        echo    ✅ Simplified Gunicorn setup
        echo    ✅ Removed default nginx site
        echo    ✅ Added nginx config test
        echo.
    ) else (
        echo ⚠️ Health check failed. Checking logs...
        echo.
        echo 📋 Container logs:
        docker compose logs
        echo.
        echo 🔧 Try these commands to debug:
        echo    docker compose logs -f
        echo    docker compose exec skillbridge nginx -t
        echo    docker compose exec skillbridge ps aux
    )
) else (
    echo ⚠️ curl not available - cannot test health endpoint
    echo You can manually test: http://localhost/health
    echo.
    echo 🎉 Redeploy completed!
    echo Your application should be available at: http://localhost
)

echo.
echo ✅ Redeploy script completed!
pause