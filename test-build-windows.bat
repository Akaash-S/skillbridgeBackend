@echo off
echo 🧪 Testing SkillBridge Docker Build (Windows)
echo =============================================
echo.

REM Check Docker installation
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed or not running
    echo Please install Docker Desktop for Windows and ensure it's running
    pause
    exit /b 1
)

REM Check Docker Compose
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not available
    echo Please ensure Docker Desktop is running properly
    pause
    exit /b 1
)

echo ✅ Docker prerequisites check passed
docker --version
docker compose version
echo.

REM Check required files
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

REM Check .env file
if not exist ".env" (
    echo ⚠️ .env file not found. Creating minimal test configuration...
    echo SECRET_KEY=test-secret-key-for-build-only > .env
    echo FLASK_ENV=production >> .env
    echo PORT=8000 >> .env
    echo DISABLE_FIREBASE=true >> .env
    echo GEMINI_API_KEY=test-key >> .env
    echo YOUTUBE_API_KEY=test-key >> .env
    echo ADZUNA_APP_ID=test-id >> .env
    echo ADZUNA_APP_KEY=test-key >> .env
    echo MFA_ISSUER_NAME=SkillBridge >> .env
    echo MFA_SECRET_KEY=test-mfa-key >> .env
    echo SMTP_HOST=smtp.gmail.com >> .env
    echo SMTP_PORT=587 >> .env
    echo SMTP_USER=test@example.com >> .env
    echo SMTP_PASSWORD=test-password >> .env
    echo SMTP_USE_TLS=true >> .env
    echo EMAIL_FROM_NAME=SkillBridge >> .env
    echo EMAIL_SUPPORT=test@example.com >> .env
    echo EMAIL_RATE_LIMIT=10 >> .env
    echo EMAIL_BATCH_SIZE=50 >> .env
    echo CORS_ORIGINS=http://localhost:8080 >> .env
    echo ⚠️ Created minimal .env file for testing
)

echo ✅ Configuration file ready
echo.

REM Clean up previous builds
echo 🧹 Cleaning up previous builds...
docker compose down --remove-orphans 2>nul
echo ✅ Cleanup completed
echo.

REM Test Docker build
echo 🏗️ Testing Docker build (this may take several minutes)...
docker compose build --no-cache --progress=plain
if %errorlevel% neq 0 (
    echo ❌ Docker build failed!
    echo.
    echo 🔧 Common solutions:
    echo 1. Ensure Docker Desktop is running
    echo 2. Check available disk space
    echo 3. Try: docker system prune -a
    echo 4. Restart Docker Desktop
    pause
    exit /b 1
)

echo ✅ Docker build completed successfully!
echo.

REM Test container startup
echo 🚀 Testing container startup...
docker compose up -d
if %errorlevel% neq 0 (
    echo ❌ Container startup failed!
    echo.
    echo Container logs:
    docker compose logs
    pause
    exit /b 1
)

echo ✅ Container started successfully!
echo.

REM Wait for services to initialize
echo ⏳ Waiting for services to initialize...
timeout /t 20 /nobreak >nul

REM Check container status
echo 📊 Checking container status...
docker compose ps
echo.

REM Test health endpoint (if curl is available)
echo 🏥 Testing health endpoint...
curl --version >nul 2>&1
if %errorlevel% equ 0 (
    curl -f -s http://localhost/health >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ Health check passed!
    ) else (
        echo ⚠️ Health check failed - application may still be starting
    )
) else (
    echo ⚠️ curl not available - skipping health check
    echo You can manually test: http://localhost/health
)
echo.

REM Show recent logs
echo 📋 Recent container logs:
docker compose logs --tail=10
echo.

REM Cleanup test containers
echo 🧹 Cleaning up test containers...
docker compose down
echo ✅ Test containers stopped
echo.

echo 🎉 Build test completed successfully!
echo =====================================
echo.
echo 📋 Your Dockerfile is working correctly. Next steps:
echo 1. Ensure your .env file has real configuration values
echo 2. Deploy with: deploy-windows.bat
echo 3. Or manually: docker compose up -d
echo.
echo 🔧 If you encounter issues during deployment:
echo - Check logs: docker compose logs -f
echo - Restart: docker compose restart
echo - Rebuild: docker compose build --no-cache
echo.

pause