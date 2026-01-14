#!/bin/bash

# Backend Status Checker for Google Compute Engine

echo "🔍 SkillBridge Backend Status Check"
echo "==================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo "1. 🐳 Docker Container Status:"
echo "=============================="
if docker-compose ps 2>/dev/null; then
    container_status=$(docker-compose ps --services --filter "status=running" 2>/dev/null)
    if [ -n "$container_status" ]; then
        print_success "Backend container is running"
    else
        print_error "Backend container is not running"
        echo "Fix: docker-compose up -d --build"
    fi
else
    print_error "docker-compose not available or not in backend directory"
fi

echo ""
echo "2. 🌐 Port 8080 Status:"
echo "======================="
if netstat -tlnp 2>/dev/null | grep -q ":8080"; then
    print_success "Port 8080 is in use"
    netstat -tlnp | grep ":8080"
elif ss -tlnp 2>/dev/null | grep -q ":8080"; then
    print_success "Port 8080 is in use"
    ss -tlnp | grep ":8080"
else
    print_error "Nothing listening on port 8080"
fi

echo ""
echo "3. 🏥 Health Check:"
echo "=================="
if curl -f -m 5 http://localhost:8080/health &> /dev/null; then
    print_success "Backend health check passed"
    echo "Response:"
    curl -s http://localhost:8080/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8080/health
else
    print_error "Backend health check failed"
    echo "Backend is not responding on localhost:8080"
fi

echo ""
echo "4. 🔧 Environment Check:"
echo "========================"
if [ -f ".env" ]; then
    print_success ".env file exists"
    echo "CORS_ORIGINS: $(grep "^CORS_ORIGINS=" .env | cut -d'=' -f2 || echo "Not set")"
    echo "PORT: $(grep "^PORT=" .env | cut -d'=' -f2 || echo "Not set")"
else
    print_error ".env file not found"
fi

echo ""
echo "5. 📋 Recent Logs:"
echo "=================="
if docker-compose logs --tail=10 2>/dev/null; then
    echo "Logs retrieved successfully"
else
    print_warning "Could not retrieve logs"
fi

echo ""
echo "6. 🌍 External Access Test:"
echo "==========================="
if curl -f -m 10 -I https://skillbridge-server.asolvitra.tech/health &> /dev/null; then
    print_success "External endpoint is accessible"
    curl -I https://skillbridge-server.asolvitra.tech/health
else
    print_warning "External endpoint not accessible"
    echo "This could be normal if Nginx is not configured yet"
fi

echo ""
echo "🔧 Quick Fix Commands:"
echo "====================="
echo "Start backend:     docker-compose up -d --build"
echo "View logs:         docker-compose logs -f"
echo "Restart:           docker-compose restart"
echo "Check status:      docker-compose ps"
echo "Test health:       curl http://localhost:8080/health"
echo "Test external:     curl -I https://skillbridge-server.asolvitra.tech/health"
echo ""