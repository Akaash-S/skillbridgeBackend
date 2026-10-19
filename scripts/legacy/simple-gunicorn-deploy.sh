#!/bin/bash

# Simple Gunicorn-only deployment (no Nginx complications)
set -e

echo "🚀 Simple Gunicorn Deployment"
echo "============================="
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

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please create it with your configuration."
    exit 1
fi

print_success "Environment configuration found"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
print_success "Directories created"

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker compose down --remove-orphans 2>/dev/null || true
print_success "Existing containers stopped"

# Clean up
echo "🧹 Cleaning up..."
docker system prune -f 2>/dev/null || true
print_success "Cleanup completed"

# Build the application
echo "🏗️  Building simplified application (Gunicorn only)..."
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
sleep 15

# Check if containers are running
echo "📊 Checking container status..."
docker compose ps

# Test health endpoint
echo "🏥 Testing health endpoint..."
sleep 5

# Try both port 80 and 8000
HEALTH_PASSED=false

if curl -f -s http://localhost/health > /dev/null 2>&1; then
    print_success "Health check passed on port 80!"
    HEALTH_PASSED=true
elif curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    print_success "Health check passed on port 8000!"
    HEALTH_PASSED=true
fi

if [ "$HEALTH_PASSED" = true ]; then
    # Get server IP
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
    
    echo ""
    echo "🎉 Deployment successful!"
    echo "======================="
    echo ""
    echo "🔗 Your application is available at:"
    echo "   Local (port 80):  http://localhost"
    echo "   Local (port 8000): http://localhost:8000"
    echo "   External (port 80): http://$SERVER_IP"
    echo "   External (port 8000): http://$SERVER_IP:8000"
    echo "   Health check: http://localhost:8000/health"
    echo ""
    echo "📋 Architecture:"
    echo "   ✅ Direct Gunicorn deployment (no Nginx)"
    echo "   ✅ Port 8000 mapped to port 80"
    echo "   ✅ Simplified, reliable setup"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs:    docker compose logs -f"
    echo "   Restart:      docker compose restart"
    echo "   Stop:         docker compose down"
    echo "   Status:       docker compose ps"
    echo ""
    
else
    print_warning "Health check failed. Checking logs..."
    echo ""
    echo "📋 Container logs:"
    docker compose logs --tail=30
    echo ""
    echo "🔧 Debug commands:"
    echo "   docker compose logs -f"
    echo "   docker compose exec skillbridge ps aux"
    echo "   docker compose exec skillbridge curl http://localhost:8000/health"
fi

echo "✅ Deployment script completed!"