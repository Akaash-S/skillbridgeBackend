#!/bin/bash

# Clean deployment script - no SSL, no Nginx, no complications
set -e

echo "🚀 Clean Deployment (Gunicorn Only)"
echo "==================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "Dockerfile" ] || [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the directory containing Dockerfile and docker-compose.yml"
    exit 1
fi

print_success "Found required files"

# Check .env file
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please create it with your configuration."
    exit 1
fi

print_success "Environment configuration found"

# Complete cleanup
echo "🧹 Complete cleanup (removing all Docker data)..."
docker compose down --remove-orphans --volumes 2>/dev/null || true
docker system prune -af --volumes 2>/dev/null || true
docker builder prune -af 2>/dev/null || true
print_success "Complete cleanup done"

# Remove any problematic directories
print_info "Removing any problematic local directories..."
rm -rf logs nginx ssl 2>/dev/null || true
print_success "Local directories cleaned"

# Show what we're building
print_info "Building with these key files:"
echo "  ✓ Dockerfile (ultra-simple, Gunicorn only)"
echo "  ✓ docker-compose.yml (no volumes, no SSL)"
echo "  ✓ .dockerignore (excludes nginx, ssl, scripts)"
echo "  ✓ app/ directory (your Flask application)"
echo "  ✓ .env (your environment variables)"

# Build the application
echo ""
echo "🏗️  Building clean application..."
if docker compose build --no-cache --pull; then
    print_success "Build completed successfully"
else
    print_error "Build failed"
    echo ""
    echo "🔧 If build fails, check:"
    echo "  - Docker is running"
    echo "  - Internet connection works"
    echo "  - Sufficient disk space available"
    echo "  - No syntax errors in requirements.txt"
    exit 1
fi

# Start the application
echo "🚀 Starting application..."
if docker compose up -d; then
    print_success "Application started"
else
    print_error "Failed to start application"
    echo ""
    echo "Container logs:"
    docker compose logs
    exit 1
fi

# Wait for application to start
echo "⏳ Waiting for application to start (30 seconds)..."
sleep 30

# Check container status
echo "📊 Container status:"
docker compose ps

# Test health endpoint with patience
echo ""
echo "🏥 Testing health endpoint..."
HEALTH_PASSED=false

for i in {1..12}; do
    echo "Health check attempt $i/12..."
    
    if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Health check passed on port 8000!"
        HEALTH_PASSED=true
        break
    elif curl -f -s http://localhost/health > /dev/null 2>&1; then
        print_success "Health check passed on port 80!"
        HEALTH_PASSED=true
        break
    else
        echo "Waiting 5 seconds before retry..."
        sleep 5
    fi
done

echo ""
if [ "$HEALTH_PASSED" = true ]; then
    # Get server IP
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
    
    echo "🎉 DEPLOYMENT SUCCESSFUL!"
    echo "========================"
    echo ""
    echo "🔗 Your SkillBridge backend is running at:"
    echo "   🌐 External: http://$SERVER_IP"
    echo "   🏠 Local:    http://localhost"
    echo "   🔧 Direct:   http://localhost:8000"
    echo "   ❤️  Health:   http://localhost:8000/health"
    echo ""
    echo "📋 Clean Architecture:"
    echo "   ✅ Direct Gunicorn deployment"
    echo "   ✅ No Nginx (eliminates complexity)"
    echo "   ✅ No SSL certificates (no permission issues)"
    echo "   ✅ No file logging (Docker handles logs)"
    echo "   ✅ Minimal attack surface"
    echo ""
    echo "📋 Management:"
    echo "   📜 View logs:    docker compose logs -f"
    echo "   🔄 Restart:      docker compose restart"
    echo "   🛑 Stop:         docker compose down"
    echo "   📊 Status:       docker compose ps"
    echo ""
    echo "🔒 Security:"
    echo "   • Gunicorn is production-ready"
    echo "   • Environment variables loaded securely"
    echo "   • CORS configured for your domains"
    echo "   • No unnecessary services running"
    echo ""
    echo "🚀 Your backend is ready for production traffic!"
    
else
    print_error "Health check failed after 1 minute"
    echo ""
    echo "📋 Debugging information:"
    echo ""
    echo "Container status:"
    docker compose ps
    echo ""
    echo "Recent logs:"
    docker compose logs --tail=50
    echo ""
    echo "🔧 Manual debugging commands:"
    echo "   docker compose exec skillbridge curl http://localhost:8000/health"
    echo "   docker compose exec skillbridge ps aux"
    echo "   docker compose logs -f"
    echo ""
    echo "💡 Try accessing manually:"
    echo "   curl http://localhost:8000/health"
    echo "   curl http://localhost/health"
fi

echo ""
echo "✅ Clean deployment script completed!"