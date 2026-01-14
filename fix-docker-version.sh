#!/bin/bash

# Fix Docker Version Issue - Upgrade Docker and Docker Compose

echo "🔧 Fixing Docker Version Issue"
echo "=============================="

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

# Check current Docker version
print_status "Checking current Docker version..."
docker --version || print_error "Docker not installed"
docker-compose --version || print_error "Docker Compose not installed"

# Stop any running containers first
print_status "Stopping any running containers..."
docker-compose down 2>/dev/null || true

# Remove old Docker versions
print_status "Removing old Docker versions..."
sudo apt-get remove -y docker docker-engine docker.io containerd runc docker-compose 2>/dev/null || true

# Update package index
print_status "Updating package index..."
sudo apt-get update

# Install prerequisites
print_status "Installing prerequisites..."
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
print_status "Adding Docker GPG key..."
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up Docker repository
print_status "Setting up Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index again
print_status "Updating package index with Docker repository..."
sudo apt-get update

# Install latest Docker Engine
print_status "Installing latest Docker Engine..."
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
print_status "Adding user to docker group..."
sudo usermod -aG docker $USER

# Install Docker Compose (standalone) - latest version
print_status "Installing latest Docker Compose..."
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create symlink for docker compose plugin
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Start and enable Docker service
print_status "Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
print_status "Verifying Docker installation..."
echo "Docker version:"
sudo docker --version

echo "Docker Compose version:"
sudo docker-compose --version

# Test Docker
print_status "Testing Docker..."
if sudo docker run --rm hello-world > /dev/null 2>&1; then
    print_success "Docker is working correctly"
else
    print_error "Docker test failed"
fi

print_success "Docker upgrade completed!"
echo ""
print_warning "IMPORTANT: You need to log out and log back in for group changes to take effect"
echo "Or run: newgrp docker"
echo ""
echo "🔧 Next steps:"
echo "1. Log out and log back in (or run: newgrp docker)"
echo "2. Test: docker --version"
echo "3. Test: docker-compose --version"
echo "4. Run deployment: ./deploy-gce.sh"
echo ""