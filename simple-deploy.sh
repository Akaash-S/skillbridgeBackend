#!/bin/bash

# Simple deployment script for GCP with your current environment
set -e

echo "🚀 Simple SkillBridge Deployment"
echo "==============================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please create it with your configuration."
    exit 1
fi

print_success "Found required files"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs nginx/ssl
print_success "Directories created"

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker compose down --remove-orphans 2>/dev/null || true
print_success "Existing containers stopped"

# Build the application
echo "🏗️  Building application..."
if docker compose build --no-cache; then
    print_success "Build completed successfully"
else
    print_error "Build failed"
    exit 1
fi

# Start the application
echo "🚀 Starting application..."
if docker compose up -d; then
    print_success "Application started"
else
    print_error "Failed to start application"
    exit 1
fi

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 20

# Check if containers are running
echo "📊 Checking container status..."
docker compose ps

# Test health endpoint
echo "🏥 Testing health endpoint..."
if curl -f -s http://localhost/health > /dev/null 2>&1; then
    print_success "Health check passed!"
    
    # Get server IP
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
    
    echo ""
    echo "🎉 Deployment successful!"
    echo "======================="
    echo ""
    echo "🔗 Your application is available at:"
    echo "   Local:    http://localhost"
    echo "   External: http://$SERVER_IP"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs:    docker compose logs -f"
    echo "   Restart:      docker compose restart"
    echo "   Stop:         docker compose down"
    echo "   Status:       docker compose ps"
    echo ""
    
else
    print_warning "Health check failed. Application may still be starting..."
    echo ""
    echo "📋 Check logs with: docker compose logs -f"
    echo "📋 Check status with: docker compose ps"
fi

echo "✅ Deployment script completed!"