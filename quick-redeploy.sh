#!/bin/bash

# Quick redeploy script with fixed Dockerfile
set -e

echo "🔧 Quick Redeploy - Fixed Dockerfile"
echo "===================================="
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

print_success "Found required files"

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker compose down --remove-orphans 2>/dev/null || true
print_success "Containers stopped"

# Clean up Docker cache
echo "🧹 Cleaning Docker cache..."
docker system prune -f 2>/dev/null || true
print_success "Cache cleaned"

# Build with the fixed Dockerfile
echo "🏗️  Building with fixed Dockerfile (no Redis, fixed configs)..."
if docker compose build --no-cache --progress=plain; then
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
sleep 15

# Check container status
echo "📊 Checking container status..."
docker compose ps

# Show logs
echo "📋 Recent logs:"
docker compose logs --tail=20

# Test health endpoint
echo "🏥 Testing health endpoint..."
sleep 5
if curl -f -s http://localhost/health > /dev/null 2>&1; then
    print_success "Health check passed!"
    
    # Get server IP
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
    
    echo ""
    echo "🎉 Redeploy successful!"
    echo "====================="
    echo ""
    echo "🔗 Your application is available at:"
    echo "   Local:    http://localhost"
    echo "   External: http://$SERVER_IP"
    echo "   Health:   http://localhost/health"
    echo ""
    echo "📋 Key fixes applied:"
    echo "   ✅ Removed Redis (not needed)"
    echo "   ✅ Fixed Nginx configuration"
    echo "   ✅ Simplified Gunicorn setup"
    echo "   ✅ Removed default nginx site"
    echo "   ✅ Added nginx config test"
    echo ""
    
else
    print_warning "Health check failed. Checking logs..."
    echo ""
    echo "📋 Container logs:"
    docker compose logs
    echo ""
    echo "🔧 Try these commands to debug:"
    echo "   docker compose logs -f"
    echo "   docker compose exec skillbridge nginx -t"
    echo "   docker compose exec skillbridge ps aux"
fi

echo "✅ Redeploy script completed!"