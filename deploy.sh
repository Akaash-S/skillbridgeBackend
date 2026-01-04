#!/bin/bash

# SkillBridge Suite Backend Deployment Script
# This script automates the deployment process for production

set -e  # Exit on any error

echo "🚀 SkillBridge Suite Backend Deployment"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    print_warning "Please copy .env.example to .env and configure your environment variables"
    exit 1
fi

print_status "Environment file found ✓"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed!"
    print_warning "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

print_status "Docker is installed ✓"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed!"
    print_warning "Please install Docker Compose first"
    exit 1
fi

print_status "Docker Compose is installed ✓"

# Check if credentials directory exists
if [ ! -d "credentials" ]; then
    print_warning "credentials/ directory not found"
    print_warning "Creating credentials directory..."
    mkdir -p credentials
    print_warning "Please add your firebase-service-account.json to the credentials/ directory"
fi

# Check if Firebase service account file exists
if [ ! -f "credentials/firebase-service-account.json" ]; then
    print_error "Firebase service account file not found!"
    print_warning "Please add firebase-service-account.json to the credentials/ directory"
    exit 1
fi

print_status "Firebase credentials found ✓"

# Check if SSL certificates exist (for production)
if [ ! -d "ssl" ]; then
    print_warning "ssl/ directory not found"
    print_warning "Creating ssl directory for certificates..."
    mkdir -p ssl
    print_warning "For production, please add SSL certificates to the ssl/ directory"
fi

# Build and deploy
print_status "Building Docker images..."
docker-compose build

print_status "Starting services..."
docker-compose up -d

# Wait for services to start
print_status "Waiting for services to start..."
sleep 10

# Check if backend is healthy
print_status "Checking backend health..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "Backend is healthy ✓"
else
    print_error "Backend health check failed!"
    print_warning "Check logs with: docker-compose logs skillbridge-backend"
    exit 1
fi

# Show running containers
print_status "Deployment completed successfully!"
echo ""
echo "Running containers:"
docker-compose ps

echo ""
echo "🎉 SkillBridge Suite Backend is now running!"
echo ""
echo "📍 Endpoints:"
echo "   • Health Check: http://localhost:8000/health"
echo "   • API Base URL: http://localhost:8000"
echo ""
echo "🔧 Management Commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop services: docker-compose down"
echo "   • Restart: docker-compose restart"
echo ""
echo "📊 Monitoring:"
echo "   • Backend logs: docker-compose logs -f skillbridge-backend"
echo "   • Nginx logs: docker-compose logs -f nginx"
echo ""

# Optional: Seed database
read -p "Would you like to seed the database with initial data? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Seeding database..."
    docker-compose exec skillbridge-backend python seed_data.py
    print_status "Database seeding completed ✓"
fi

print_status "Deployment script completed!"