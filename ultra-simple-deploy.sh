#!/bin/bash

# Ultra-simple deployment with no file logging issues
set -e

echo "🚀 Ultra-Simple Deployment (No File Logging)"
echo "============================================="
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

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker compose down --remove-orphans 2>/dev/null || true
print_success "Existing containers stopped"

# Clean up
echo "🧹 Cleaning up..."
docker system prune -f 2>/dev/null || true
print_success "Cleanup completed"

# Build the application
echo "🏗️  Building ultra-simple application..."
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
echo "⏳ Waiting for application to start..."
sleep 20

# Check if containers are running
echo "📊 Checking container status..."
docker compose ps

# Test health endpoint with multiple attempts
echo "🏥 Testing health endpoint..."
HEALTH_PASSED=false
for i in {1..10}; do
    echo "Attempt $i/10..."
    if curl -f -s http://localhost/health > /dev/null 2>&1; then
        print_success "Health check passed on port 80!"
        HEALTH_PASSED=true
        break
    elif curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Health check passed on port 8000!"
        HEALTH_PASSED=true
        break
    else
        echo "Health check failed, retrying in 5 seconds..."
        sleep 5
    fi
done

if [ "$HEALTH_PASSED" = true ]; then
    # Get server IP
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
    
    echo ""
    echo "🎉 Deployment successful!"
    echo "======================="
    echo ""
    echo "🔗 Your application is available at:"
    echo "   External: http://$SERVER_IP"
    echo "   Local:    http://localhost"
    echo "   Direct:   http://localhost:8000"
    echo "   Health:   http://localhost:8000/health"
    echo ""
    echo "📋 Simple Architecture:"
    echo "   ✅ Direct Gunicorn (no Nginx, no file logging)"
    echo "   ✅ All logs via Docker (docker compose logs)"
    echo "   ✅ Port 8000 → 80 mapping"
    echo "   ✅ Zero configuration complexity"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs:    docker compose logs -f"
    echo "   Restart:      docker compose restart"
    echo "   Stop:         docker compose down"
    echo "   Status:       docker compose ps"
    echo ""
    
else
    print_warning "Health check failed after 10 attempts. Checking logs..."
    echo ""
    echo "📋 Container logs:"
    docker compose logs --tail=50
    echo ""
    echo "🔧 Debug commands:"
    echo "   docker compose logs -f"
    echo "   docker compose exec skillbridge ps aux"
    echo "   docker compose exec skillbridge curl http://localhost:8000/health"
    echo ""
    echo "💡 The application might still be starting up. Try:"
    echo "   curl http://localhost:8000/health"
    echo "   curl http://localhost/health"
fi

echo "✅ Deployment script completed!"