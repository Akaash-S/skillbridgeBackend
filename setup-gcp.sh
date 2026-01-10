#!/bin/bash

# SkillBridge Backend - GCP Setup Script
# This script helps set up the local development environment for GCP deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info "Setting up SkillBridge Backend for GCP deployment..."

# Check if running in backend directory
if [ ! -f "requirements.txt" ]; then
    print_error "Please run this script from the backend directory"
    exit 1
fi

# Create .env file from template if it doesn't exist
if [ ! -f ".env" ]; then
    print_info "Creating .env file from template..."
    cp .env.gcp .env
    print_warning "Please update .env file with your actual values"
else
    print_info ".env file already exists"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
print_info "Installing dependencies..."
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || {
    print_error "Failed to activate virtual environment"
    exit 1
}

pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn  # Ensure gunicorn is installed

print_success "Dependencies installed"

# Create credentials directory
if [ ! -d "credentials" ]; then
    print_info "Creating credentials directory..."
    mkdir credentials
    print_warning "Please place your Firebase service account JSON file in the credentials/ directory"
else
    print_info "Credentials directory already exists"
fi

# Check for Firebase service account file
if [ ! -f "credentials/firebase-service-account.json" ]; then
    print_warning "Firebase service account file not found"
    print_info "Please download your Firebase service account key and save it as:"
    print_info "credentials/firebase-service-account.json"
fi

# Test local build
print_info "Testing Docker build..."
if command -v docker &> /dev/null; then
    docker build -t skillbridge-backend-test . --quiet
    print_success "Docker build successful"
    
    # Clean up test image
    docker rmi skillbridge-backend-test --force &>/dev/null || true
else
    print_warning "Docker not found. Please install Docker to test builds locally"
fi

print_success "Setup completed!"
print_info ""
print_info "Next steps:"
print_info "1. Update .env file with your actual values"
print_info "2. Place Firebase service account JSON in credentials/ directory"
print_info "3. Test locally: python run.py"
print_info "4. Deploy to GCP: ./deploy.sh cloud-run your-project-id"
print_info ""
print_info "For detailed deployment instructions, see GCP_DEPLOYMENT_GUIDE.md"