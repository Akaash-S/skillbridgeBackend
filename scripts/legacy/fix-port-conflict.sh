#!/bin/bash

# Fix port 80 conflict between Docker and Nginx
set -e

echo "🔧 Fixing Port 80 Conflict"
echo "=========================="
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

# Check what's using port 80
echo "🔍 Checking what's using port 80..."
PORT_80_USERS=$(sudo netstat -tulnp | grep ":80 " || echo "")

if [ -z "$PORT_80_USERS" ]; then
    print_success "Port 80 is free"
else
    print_warning "Port 80 is in use:"
    echo "$PORT_80_USERS"
    echo ""
fi

# Check if Docker is using port 80
DOCKER_PORT_80=$(docker ps --format "table {{.Names}}\t{{.Ports}}" | grep ":80->" || echo "")
if [ ! -z "$DOCKER_PORT_80" ]; then
    print_warning "Docker containers using port 80:"
    echo "$DOCKER_PORT_80"
    echo ""
    
    echo "🛑 Stopping Docker containers to free port 80..."
    docker compose down 2>/dev/null || true
    print_success "Docker containers stopped"
else
    print_info "Docker is not using port 80"
fi

# Check if Nginx is installed and running
if command -v nginx &> /dev/null; then
    print_info "Nginx is installed"
    
    if systemctl is-active --quiet nginx; then
        print_success "Nginx is running"
    else
        print_warning "Nginx is installed but not running"
        echo "🚀 Starting Nginx..."
        sudo systemctl start nginx
        if systemctl is-active --quiet nginx; then
            print_success "Nginx started successfully"
        else
            print_error "Failed to start Nginx"
            sudo systemctl status nginx
        fi
    fi
else
    print_warning "Nginx is not installed"
fi

# Update docker-compose.yml to avoid port 80 conflict
echo "🐳 Updating Docker configuration to avoid port conflicts..."

# Backup current docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    cp docker-compose.yml docker-compose.yml.backup
    print_success "Backed up docker-compose.yml"
fi

# Create new docker-compose.yml that only uses port 8000
cat > docker-compose.yml << 'EOF'
# Docker Compose file for SkillBridge Backend - No Port Conflicts

services:
  skillbridge:
    build: 
      context: .
      dockerfile: Dockerfile
    container_name: skillbridge-app
    ports:
      - "127.0.0.1:8000:8000"  # Only bind to localhost:8000 (no port 80)
    environment:
      # Flask Configuration
      - SECRET_KEY=${SECRET_KEY}
      - FLASK_ENV=${FLASK_ENV:-production}
      
      # Production Port Configuration
      - PORT=${PORT:-8000}
      
      # Firebase Configuration
      - FIREBASE_SERVICE_ACCOUNT_BASE64=${FIREBASE_SERVICE_ACCOUNT_BASE64}
      - DISABLE_FIREBASE=${DISABLE_FIREBASE:-false}
      
      # Gemini AI Configuration
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - YOUTUBE_API_KEY=${YOUTUBE_API_KEY}
      
      # Adzuna Jobs API Configuration
      - ADZUNA_APP_ID=${ADZUNA_APP_ID}
      - ADZUNA_APP_KEY=${ADZUNA_APP_KEY}
      
      # MFA Configuration
      - MFA_ISSUER_NAME=${MFA_ISSUER_NAME}
      - MFA_SECRET_KEY=${MFA_SECRET_KEY}
      
      # SMTP Email Configuration
      - SMTP_HOST=${SMTP_HOST:-smtp.gmail.com}
      - SMTP_PORT=${SMTP_PORT:-587}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - SMTP_USE_TLS=${SMTP_USE_TLS:-true}
      
      # Email Settings
      - EMAIL_FROM_NAME=${EMAIL_FROM_NAME}
      - EMAIL_SUPPORT=${EMAIL_SUPPORT}
      - EMAIL_RATE_LIMIT=${EMAIL_RATE_LIMIT}
      - EMAIL_BATCH_SIZE=${EMAIL_BATCH_SIZE}
      
      # CORS Configuration
      - CORS_ORIGINS=${CORS_ORIGINS}
      
    restart: unless-stopped
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
      
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

networks:
  default:
    name: skillbridge-network
EOF

print_success "Updated docker-compose.yml (no port 80 binding)"

# Start Docker with new configuration
echo "🚀 Starting Docker with new configuration..."
docker compose up -d

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 15

# Test if application is running
if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    print_success "Application is running on localhost:8000"
else
    print_error "Application is not responding on localhost:8000"
    echo "Check logs: docker compose logs -f"
    exit 1
fi

# Final port check
echo ""
echo "📊 Final Port Status:"
echo "Port 80 usage:"
sudo netstat -tulnp | grep ":80 " || echo "   ✅ Port 80 is free"

echo ""
echo "Port 8000 usage:"
sudo netstat -tulnp | grep ":8000 " || echo "   ⚠️  Port 8000 not detected (may be Docker internal)"

echo ""
echo "Docker containers:"
docker compose ps

echo ""
echo "✅ Port conflict resolution completed!"
echo ""
echo "📋 Current setup:"
echo "   🐳 Docker: localhost:8000 only (no external port 80)"
echo "   🌐 Nginx: Can now use port 80 for domain setup"
echo "   🔗 Access: http://127.0.0.1:8000/health"
echo ""
echo "🚀 Next steps:"
echo "   1. Run: sudo ./domain-setup-fixed.sh"
echo "   2. This will set up Nginx on port 80 to proxy to Docker on port 8000"
echo ""