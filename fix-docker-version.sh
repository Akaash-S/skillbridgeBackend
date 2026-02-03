#!/bin/bash

# Docker Version Fix Script
# Fixes "client version 1.43 is too old" error by installing latest Docker

set -e

echo "🔧 Docker Version Fix Script"
echo "============================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check current Docker version
print_step "Checking current Docker installation..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "Current Docker version: $DOCKER_VERSION"
    
    # Test Docker API
    if docker version &> /dev/null; then
        print_success "Docker is working correctly"
        echo "No fix needed. If you're still getting API version errors, try:"
        echo "  docker compose version"
        echo "  docker --version"
        exit 0
    else
        print_warning "Docker API version issue detected"
    fi
else
    print_warning "Docker not found"
fi

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root. This script will work but it's not recommended."
fi

print_step "Removing old Docker installations..."

# Stop Docker service
sudo systemctl stop docker 2>/dev/null || true

# Remove old Docker packages
sudo apt-get remove -y docker docker-engine docker.io containerd runc docker-compose 2>/dev/null || true

# Remove old repositories and keys
sudo rm -f /etc/apt/sources.list.d/docker.list
sudo rm -f /etc/apt/keyrings/docker.gpg
sudo rm -f /usr/local/bin/docker-compose

print_success "Old Docker installations removed"

print_step "Installing latest Docker..."

# Update package index
sudo apt-get update

# Install prerequisites
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index
sudo apt-get update

# Install Docker Engine
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

print_success "Latest Docker installed"

print_step "Configuring Docker..."

# Add user to docker group
sudo usermod -aG docker $USER

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Create docker-compose symlink for compatibility
sudo ln -sf /usr/libexec/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose 2>/dev/null || true

print_success "Docker configured"

print_step "Testing Docker installation..."

# Test Docker with sudo first
if sudo docker run hello-world &> /dev/null; then
    print_success "Docker engine is working"
else
    print_error "Docker engine test failed"
    exit 1
fi

# Check Docker Compose
if docker compose version &> /dev/null; then
    print_success "Docker Compose V2 is working"
elif command -v docker-compose &> /dev/null && docker-compose --version &> /dev/null; then
    print_success "Docker Compose V1 is working"
else
    print_warning "Docker Compose may need manual configuration"
fi

echo ""
print_success "Docker installation completed successfully!"
echo ""
echo "📋 Installed versions:"
sudo docker --version
docker compose version 2>/dev/null || docker-compose --version 2>/dev/null || echo "Docker Compose: Not available"
echo ""
echo "⚠️  IMPORTANT: You need to logout and login again for group changes to take effect"
echo ""
echo "🔧 After logout/login, test with:"
echo "   docker --version"
echo "   docker compose version"
echo "   docker run hello-world"
echo ""
echo "🚀 Then you can continue with your deployment:"
echo "   docker compose build --no-cache"
echo "   docker compose up -d"
echo ""

# Check if we're in an application directory
if [ -f "docker-compose.yml" ] || [ -f "Dockerfile" ]; then
    echo "📍 Application files detected in current directory"
    echo "   After logout/login, you can run:"
    echo "   docker compose build --no-cache"
    echo "   docker compose up -d"
fi

print_warning "Please logout and login again, then test Docker without sudo"