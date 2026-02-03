@echo off
echo 🚀 SkillBridge Windows Deployment Script
echo ========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed or not in PATH
    echo Please install Docker Desktop for Windows first
    pause
    exit /b 1
)

REM Check if Docker Compose is available
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not available
    echo Please ensure Docker Desktop is running
    pause
    exit /b 1
)

echo ✅ Docker is available
docker --version
docker compose version
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

REM Create necessary directories
echo 📁 Creating directories...
if not exist "logs" mkdir logs
if not exist "nginx\ssl" mkdir nginx\ssl
echo ✅ Directories created
echo.

REM Stop existing containers
echo 🛑 Stopping existing containers...
docker compose down --remove-orphans 2>nul
echo ✅ Existing containers stopped
echo.

REM Build the application
echo 🏗️ Building application...
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
timeout /t 20 /nobreak >nul
echo.

REM Check container status
echo 📊 Checking container status...
docker compose ps
echo.

REM Test health endpoint
echo 🏥 Testing health endpoint...
curl -f -s http://localhost/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Health check passed!
) else (
    echo ⚠️ Health check failed - application may still be starting
)
echo.

REM Get server information
echo 🎉 Deployment completed!
echo ========================
echo.
echo 🔗 Your application should be available at:
echo    Local:    http://localhost
echo    Health:   http://localhost/health
echo.
echo 📋 Useful commands:
echo    View logs:    docker compose logs -f
echo    Restart:      docker compose restart
echo    Stop:         docker compose down
echo    Status:       docker compose ps
echo.

pause