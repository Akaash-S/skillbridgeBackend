#!/bin/bash

# GCE Startup Script for SkillBridge Backend
# This script runs when the VM starts up.

# Exit on error
set -e

# Log all output to syslog
exec 1> >(logger -s -t $(basename $0)) 2>&1

echo "🚀 Starting SkillBridge Backend Setup..."

# 1. Update system and install dependencies
echo "📦 Updating system packages..."
apt-get update
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git

# 2. Install Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
else
    echo "✅ Docker already installed"
fi

# 3. Create application directory
APP_DIR="/opt/skillbridge/backend"
mkdir -p $APP_DIR
cd $APP_DIR

# 4. Pull/Setup Application
# Note: In a real scenario, you might pull from a container registry or git repo.
# For now, we assume the code or docker-compose.yml is placed here or we pull latest image.

# Example: Pull latest image if using a registry
# docker pull gcr.io/YOUR_PROJECT_ID/skillbridge-backend:latest

# 5. Start Application
if [ -f "docker-compose.yml" ]; then
    echo "🚀 Starting application with Docker Compose..."
    docker compose up -d
else
    echo "⚠️ docker-compose.yml not found. Waiting for deployment..."
fi

echo "✅ Startup script completed."
