#!/bin/bash

# Quick Docker Fix - Alternative approach using snap or direct installation

echo "🚀 Quick Docker Fix for Version Issue"
echo "===================================="

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

# Method 1: Try using Docker Compose plugin (newer approach)
print_status "Method 1: Trying Docker Compose plugin..."
if command -v docker &> /dev/null; then
    if docker compose version &> /dev/null; then
        print_success "Docker Compose plugin is available"
        echo "Use 'docker compose' instead of 'docker-compose'"
        
        # Create alias for compatibility
        echo "Creating compatibility alias..."
        echo 'alias docker-compose="docker compose"' >> ~/.bashrc
        source ~/.bashrc 2>/dev/null || true
        
        print_success "You can now use 'docker compose' or 'docker-compose'"
        exit 0
    fi
fi

# Method 2: Install latest Docker via convenience script
print_status "Method 2: Installing latest Docker via convenience script..."

# Stop any running containers
docker-compose down 2>/dev/null || true

# Download and run Docker installation script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install latest Docker Compose
print_status "Installing latest Docker Compose..."
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create symlink
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Clean up
rm -f get-docker.sh

print_success "Docker installation completed!"
echo ""
echo "📋 Verification:"
sudo docker --version
sudo docker-compose --version

echo ""
print_warning "IMPORTANT: Run 'newgrp docker' or log out/in for group changes"
echo ""
echo "🔧 Test Docker:"
echo "newgrp docker"
echo "docker --version"
echo "docker-compose --version"
echo "./deploy-gce.sh"