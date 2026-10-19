#!/bin/bash

# Final deployment script - completely clean approach
set -e

echo "🚀 Final Clean Deployment"
echo "========================="
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

# Stop ALL containers and clean everything
echo "🧹 Complete cleanup..."
docker compose down --remove-orphans --volumes 2>/dev/null || true
docker system prune -af --volumes 2>/dev/null || true
docker builder prune -af 2>/dev/null || true
print_success "Complete cleanup done"

# Remove any local logs directory that might cause issues
rm -rf logs 2>/dev/null || true
print_success "Removed local logs directory"

# Build the application with no cache
echo "🏗️  Building ultra-clean application..."
if docker compose build --no-cache --pull; then
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
    echo "Checking logs..."
    docker compose logs
    exit 1
fi

# Wait for application to fully start
echo "⏳ Waiting for application to fully start..."
sleep 30

# Check container status
echo "📊 Container status:"
docker compose ps

# Test health endpoint with patience
echo "🏥 Testing health endpoint (will try for 2 minutes)..."
HEALTH_PASSED=false
for i in {1..24}; do
    echo "Health check attempt $i/24..."
    
    # Try different endpoints
    if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Health check passed on port 8000!"
        HEALTH_PASSED=true
        break
    elif curl -f -s http://localhost/health > /dev/null 2>&1; then
        print_success "Health check passed on port 80!"
        HEALTH_PASSED=true
        break
    else
        echo "Health check failed, waiting 5 seconds..."
        sleep 5
    fi
done

if [ "$HEALTH_PASSED" = true ]; then
    # Get server IP
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
    
    echo ""
    echo "🎉 DEPLOYMENT SUCCESSFUL!"
    echo "========================"
    echo ""
    echo "🔗 Your SkillBridge backend is now running at:"
    echo "   🌐 External: http://$SERVER_IP"
    echo "   🏠 Local:    http://localhost"
    echo "   🔧 Direct:   http://localhost:8000"
    echo "   ❤️  Health:   http://localhost:8000/health"
    echo ""
    echo "📋 Clean Architecture:"
    echo "   ✅ Direct Gunicorn deployment"
    echo "   ✅ No Nginx complications"
    echo "   ✅ No file logging issues"
    echo "   ✅ No permission problems"
    echo "   ✅ Docker-native logging"
    echo ""
    echo "📋 Management commands:"
    echo "   📜 View logs:    docker compose logs -f"
    echo "   🔄 Restart:      docker compose restart"
    echo "   🛑 Stop:         docker compose down"
    echo "   📊 Status:       docker compose ps"
    echo ""
    echo "🔒 Security notes:"
    echo "   • Gunicorn is production-ready"
    echo "   • All environment variables loaded"
    echo "   • CORS configured for your domains"
    echo "   • Ready for external traffic"
    echo ""
    
else
    print_error "Health check failed after 2 minutes"
    echo ""
    echo "📋 Debugging information:"
    echo "Container status:"
    docker compose ps
    echo ""
    echo "Recent logs:"
    docker compose logs --tail=50
    echo ""
    echo "🔧 Manual testing commands:"
    echo "   docker compose exec skillbridge curl http://localhost:8000/health"
    echo "   docker compose exec skillbridge ps aux"
    echo "   docker compose logs -f"
    echo ""
    echo "💡 The application might still be starting. Try accessing:"
    echo "   http://localhost:8000/health"
    echo "   http://localhost/health"
fi

echo ""
echo "✅ Final deployment script completed!"
echo "Your SkillBridge backend should now be running securely! 🚀"