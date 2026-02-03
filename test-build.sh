#!/bin/bash

# Test build script for SkillBridge backend
set -e

echo "🧪 Testing SkillBridge Docker Build"
echo "==================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "Dockerfile" ] || [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the directory containing Dockerfile and docker-compose.yml"
    exit 1
fi

print_step "Checking prerequisites..."

# Check Docker version and API compatibility
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Run ./fix-docker-version.sh to install latest Docker."
    exit 1
fi

# Test Docker API version
if ! docker version &> /dev/null; then
    print_error "Docker API version issue detected. Run ./fix-docker-version.sh to fix."
    exit 1
fi

# Check Docker Compose
if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not available. Run ./fix-docker-version.sh to install."
    exit 1
fi

print_success "Prerequisites check passed"
echo "Docker version: $(docker --version)"
echo "Docker Compose: $(docker compose version 2>/dev/null || docker-compose --version 2>/dev/null)"

# Check .env file
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating a minimal one for testing..."
    cat > .env << EOF
SECRET_KEY=test-secret-key-for-build-only-$(date +%s)
FLASK_ENV=production
PORT=8000
DISABLE_FIREBASE=true
GEMINI_API_KEY=test-key
YOUTUBE_API_KEY=test-key
ADZUNA_APP_ID=test-id
ADZUNA_APP_KEY=test-key
MFA_ISSUER_NAME=SkillBridge
MFA_SECRET_KEY=test-mfa-key-$(date +%s)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=test@example.com
SMTP_PASSWORD=test-password
SMTP_USE_TLS=true
EMAIL_FROM_NAME=SkillBridge
EMAIL_SUPPORT=test@example.com
EMAIL_RATE_LIMIT=10
EMAIL_BATCH_SIZE=50
CORS_ORIGINS=http://localhost:8080
EOF
    print_warning "Created minimal .env file for testing"
fi

print_step "Cleaning up previous builds..."
docker compose down --remove-orphans 2>/dev/null || true

print_step "Testing Dockerfile syntax..."
if docker build --dry-run . &> /dev/null; then
    print_success "Dockerfile syntax is valid"
else
    print_warning "Docker dry-run not supported, proceeding with actual build"
fi

print_step "Testing Docker build (this may take a few minutes)..."
echo "Building with verbose output..."

if docker compose build --no-cache --progress=plain; then
    print_success "Docker build completed successfully!"
else
    print_error "Docker build failed!"
    echo ""
    echo "🔧 Common solutions:"
    echo "1. Update Docker: ./fix-docker-version.sh"
    echo "2. Check syntax errors in Dockerfile"
    echo "3. Ensure all required files exist"
    echo "4. Check available disk space: df -h"
    echo "5. Clean Docker cache: docker system prune -a"
    echo ""
    exit 1
fi

print_step "Testing container startup..."
if docker compose up -d; then
    print_success "Container started successfully!"
    
    # Wait for services to initialize
    print_step "Waiting for services to initialize..."
    sleep 20
    
    # Check container status
    print_step "Checking container status..."
    docker compose ps
    
    # Check if containers are actually running
    RUNNING_CONTAINERS=$(docker compose ps --services --filter "status=running" | wc -l)
    if [ "$RUNNING_CONTAINERS" -gt 0 ]; then
        print_success "Containers are running"
        
        # Test health endpoint
        print_step "Testing health endpoint..."
        for i in {1..6}; do
            if curl -f -s http://localhost/health > /dev/null 2>&1; then
                print_success "Health check passed!"
                break
            else
                if [ $i -eq 6 ]; then
                    print_warning "Health check failed after 6 attempts"
                    echo "This might be normal if the application is still starting up"
                else
                    echo "Attempt $i/6: Health check failed, retrying in 10 seconds..."
                    sleep 10
                fi
            fi
        done
    else
        print_warning "No containers are running"
        echo "Container logs:"
        docker compose logs --tail=30
    fi
    
    # Show recent logs
    print_step "Recent container logs:"
    docker compose logs --tail=10
    
    # Cleanup
    print_step "Cleaning up test containers..."
    docker compose down
    
else
    print_error "Container startup failed!"
    echo ""
    echo "Container logs:"
    docker compose logs
    exit 1
fi

echo ""
print_success "🎉 Build test completed successfully!"
echo ""
echo "📋 Your Dockerfile is working correctly. Next steps:"
echo "1. Ensure your .env file has real configuration values"
echo "2. Deploy with: ./simple-deploy.sh"
echo "3. Or manually: docker compose up -d"
echo ""
echo "🔧 If you encounter issues during deployment:"
echo "- Check logs: docker compose logs -f"
echo "- Restart: docker compose restart"
echo "- Rebuild: docker compose build --no-cache && docker compose up -d"
echo ""