#!/bin/bash

# Google Compute Engine Backend Deployment Script
# For SkillBridge Backend API deployment

echo "🚀 SkillBridge Backend Deployment for Google Compute Engine"
echo "=========================================================="

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

# Check Docker version compatibility
check_docker_version() {
    print_status "Checking Docker version compatibility..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo "Run: ./fix-docker-version.sh"
        exit 1
    fi
    
    # Try docker compose plugin first (newer approach)
    if docker compose version &> /dev/null; then
        print_success "Using Docker Compose plugin"
        DOCKER_COMPOSE_CMD="docker compose"
        return 0
    fi
    
    # Fall back to docker-compose standalone
    if command -v docker-compose &> /dev/null; then
        # Test if docker-compose works
        if docker-compose --version &> /dev/null; then
            print_success "Using Docker Compose standalone"
            DOCKER_COMPOSE_CMD="docker-compose"
            return 0
        else
            print_error "Docker Compose version is incompatible"
            echo "Error: client version is too old"
            echo "Fix: ./fix-docker-version.sh or ./quick-docker-fix.sh"
            exit 1
        fi
    fi
    
    print_error "Docker Compose not found"
    echo "Fix: ./fix-docker-version.sh"
    exit 1
}

# Check if we're in the backend directory
print_status "Current directory: $(pwd)"
if [ ! -f "docker-compose.yml" ] || [ ! -f "Dockerfile" ]; then
    print_error "docker-compose.yml or Dockerfile not found"
    echo "Please run this script from the backend directory:"
    echo "cd /opt/skillbridge/backend && ./deploy-gce.sh"
    exit 1
fi

# Check Docker version
check_docker_version

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found in backend directory"
    echo "Please create .env file with required environment variables"
    echo "See .env.example for reference"
    exit 1
fi

print_success "Found .env file"

# Validate required environment variables
print_status "Validating environment variables..."
required_vars=(
    "SECRET_KEY"
    "FIREBASE_SERVICE_ACCOUNT_BASE64"
    "GEMINI_API_KEY"
    "YOUTUBE_API_KEY"
    "ADZUNA_APP_ID"
    "ADZUNA_APP_KEY"
    "SMTP_HOST"
    "SMTP_USER"
    "SMTP_PASSWORD"
    "CORS_ORIGINS"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing required environment variables:"
    printf '%s\n' "${missing_vars[@]}"
    exit 1
fi

print_success "Environment validation passed"

# Stop existing containers
print_status "Stopping existing containers..."
$DOCKER_COMPOSE_CMD down --remove-orphans

# Build and start backend
print_status "Building and starting backend container..."
$DOCKER_COMPOSE_CMD up -d --build

# Wait for container to start
print_status "Waiting for backend to start..."
sleep 15

# Check container status
print_status "Checking container status..."
$DOCKER_COMPOSE_CMD ps

# Health check
print_status "Testing backend health..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:8080/health &> /dev/null; then
        print_success "Backend is responding on localhost:8080"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "Backend health check failed after $max_attempts attempts"
        echo ""
        echo "📋 Container logs:"
        $DOCKER_COMPOSE_CMD logs --tail=50
        echo ""
        echo "🔧 Troubleshooting:"
        echo "1. Check logs: $DOCKER_COMPOSE_CMD logs"
        echo "2. Check container: $DOCKER_COMPOSE_CMD ps"
        echo "3. Check port: netstat -tlnp | grep :8080"
        echo "4. Fix Docker version: ./fix-docker-version.sh"
        exit 1
    fi
    
    echo "Attempt $attempt/$max_attempts - waiting for backend..."
    sleep 2
    ((attempt++))
done

# Test the health endpoint
print_status "Testing health endpoint response..."
echo "Response from http://localhost:8080/health:"
curl -s http://localhost:8080/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8080/health

echo ""
print_success "🎉 Backend deployment completed successfully!"
echo ""
echo "📊 Deployment Summary:"
echo "   Container: skillbridge-backend"
echo "   Port: 8080"
echo "   Health: http://localhost:8080/health"
echo "   External: https://skillbridge-server.asolvitra.tech"
echo "   Docker Compose: $DOCKER_COMPOSE_CMD"
echo ""
echo "🔧 Management Commands:"
echo "   View logs: $DOCKER_COMPOSE_CMD logs -f"
echo "   Restart: $DOCKER_COMPOSE_CMD restart"
echo "   Stop: $DOCKER_COMPOSE_CMD down"
echo "   Status: $DOCKER_COMPOSE_CMD ps"
echo ""
echo "🌐 Next Steps:"
echo "1. Ensure Nginx is configured and running"
echo "2. Test external access: curl -I https://skillbridge-server.asolvitra.tech/health"
echo "3. Monitor logs: $DOCKER_COMPOSE_CMD logs -f"
echo ""

# Final test of external endpoint (if accessible)
print_status "Testing external endpoint (if accessible)..."
if curl -f -m 10 https://skillbridge-server.asolvitra.tech/health &> /dev/null; then
    print_success "External endpoint is accessible!"
else
    print_warning "External endpoint not accessible yet (this is normal if Nginx isn't configured)"
    echo "Configure Nginx to proxy requests to localhost:8080"
fi

echo ""
print_success "Deployment script completed!"