#!/bin/bash

# Update CORS origins for domain setup
set -e

echo "🔄 Updating CORS Configuration"
echo "=============================="
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

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found"
    exit 1
fi

print_success "Found .env file"

# Backup original .env
cp .env .env.backup
print_success "Created backup: .env.backup"

# Update CORS_ORIGINS in .env file
NEW_CORS="https://skillbridge.asolvitra.tech,https://www.skillbridge.asolvitra.tech,https://skillbridge.vercel.app,https://skillbridge-server.asolvitra.tech"

# Check if CORS_ORIGINS exists in .env
if grep -q "^CORS_ORIGINS=" .env; then
    # Update existing CORS_ORIGINS
    sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=$NEW_CORS|" .env
    print_success "Updated existing CORS_ORIGINS"
else
    # Add CORS_ORIGINS to .env
    echo "" >> .env
    echo "# CORS Configuration - Updated for domain" >> .env
    echo "CORS_ORIGINS=$NEW_CORS" >> .env
    print_success "Added CORS_ORIGINS to .env"
fi

echo ""
echo "📋 Updated CORS Configuration:"
echo "   Frontend domains allowed:"
echo "   ✅ https://skillbridge.asolvitra.tech"
echo "   ✅ https://www.skillbridge.asolvitra.tech"
echo "   ✅ https://skillbridge.vercel.app"
echo "   ✅ https://skillbridge-server.asolvitra.tech (backend domain)"
echo ""

# Show the current CORS setting
CURRENT_CORS=$(grep "^CORS_ORIGINS=" .env | cut -d'=' -f2)
echo "Current CORS_ORIGINS: $CURRENT_CORS"
echo ""

print_success "CORS configuration updated successfully"
echo ""
echo "🔄 Next steps:"
echo "   1. Restart your application: docker compose restart"
echo "   2. Test CORS: ./verify-domain.sh"
echo ""

# Ask if user wants to restart the application
read -p "Do you want to restart the application now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Restarting application..."
    docker compose restart
    print_success "Application restarted"
    
    echo "⏳ Waiting for application to start..."
    sleep 10
    
    # Test health endpoint
    if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        print_success "Application is responding"
    else
        print_warning "Application may still be starting up"
    fi
else
    echo "Remember to restart the application later: docker compose restart"
fi

echo ""
echo "✅ CORS update completed!"