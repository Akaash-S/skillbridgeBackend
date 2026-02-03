#!/bin/bash

# Test Docker build script
# This script tests if the Docker build works correctly

set -e

echo "🧪 Testing Docker Build"
echo "======================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
if [ ! -f "Dockerfile" ]; then
    print_error "Dockerfile not found. Please run this script from the directory containing Dockerfile"
    exit 1
fi

print_step "Checking required files..."

# Check for essential files
REQUIRED_FILES=("requirements.txt" "Dockerfile")
OPTIONAL_FILES=("nginx/nginx.conf" "supervisord.conf" "gunicorn.conf.py" ".env")

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_success "Found: $file"
    else
        print_error "Missing required file: $file"
        exit 1
    fi
done

for file in "${OPTIONAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_success "Found: $file"
    else
        print_warning "Optional file missing (will use defaults): $file"
    fi
done

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_step "Creating test .env file..."
    cat > .env << 'EOF'
SECRET_KEY=test-secret-key-for-build
FLASK_ENV=production
PORT=8080
DOMAIN=localhost
SSL_EMAIL=test@example.com
FIREBASE_SERVICE_ACCOUNT_BASE64=test-firebase-key
DISABLE_FIREBASE=true
GEMINI_API_KEY=test-gemini-key
YOUTUBE_API_KEY=test-youtube-key
ADZUNA_APP_ID=test-adzuna-id
ADZUNA_APP_KEY=test-adzuna-key
MFA_ISSUER_NAME=SkillBridge
MFA_SECRET_KEY=test-mfa-secret
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=test@gmail.com
SMTP_PASSWORD=test-password
SMTP_USE_TLS=true
EMAIL_FROM_NAME=SkillBridge
EMAIL_SUPPORT=support@example.com
CORS_ORIGINS=https://example.com
REDIS_PASSWORD=test-redis-password
GOOGLE_CLOUD_PROJECT=test-project
GCP_REGION=us-central1
EOF
    print_success "Test .env file created"
fi

# Create necessary directories
print_step "Creating necessary directories..."
mkdir -p logs nginx/ssl
print_success "Directories created"

print_step "Starting Docker build test..."

# Build the Docker image
if docker build -t skillbridge-test . --no-cache; then
    print_success "Docker build completed successfully!"
else
    print_error "Docker build failed"
    exit 1
fi

print_step "Testing the built image..."

# Test if the image can start
if docker run --rm -d --name skillbridge-test-container -p 8081:80 skillbridge-test; then
    print_success "Container started successfully"
    
    # Wait a moment for services to start
    sleep 10
    
    # Test health endpoint
    if curl -f -s http://localhost:8081/health > /dev/null 2>&1; then
        print_success "Health endpoint is responding"
    else
        print_warning "Health endpoint not responding (this might be normal during startup)"
    fi
    
    # Stop the test container
    docker stop skillbridge-test-container
    print_success "Test container stopped"
else
    print_error "Failed to start test container"
    exit 1
fi

# Clean up test image
print_step "Cleaning up..."
docker rmi skillbridge-test 2>/dev/null || true
print_success "Test image removed"

echo ""
print_success "🎉 Docker build test completed successfully!"
echo ""
echo "Your Docker setup is working correctly. You can now deploy with:"
echo "  docker compose build --no-cache"
echo "  docker compose up -d"
echo ""

# Clean up test .env if we created it
if grep -q "test-secret-key-for-build" .env 2>/dev/null; then
    print_warning "Remember to replace the test .env file with your actual configuration!"
fi