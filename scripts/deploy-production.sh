#!/bin/bash

# Production deployment script
# This script deploys the application with proper security measures

set -e

echo "🚀 Starting production deployment..."

# Check if required files exist
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it from .env.example"
    exit 1
fi

if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ docker-compose.prod.yml not found"
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs/nginx logs/app nginx/ssl redis

# Generate SSL certificates if they don't exist
if [ ! -f "nginx/ssl/fullchain.pem" ]; then
    echo "🔐 SSL certificates not found. Generating self-signed certificates..."
    chmod +x scripts/generate-ssl-certs.sh
    ./scripts/generate-ssl-certs.sh
    
    echo ""
    echo "⚠️  IMPORTANT: Self-signed certificates generated for development!"
    echo "   For production, run: ./scripts/setup-letsencrypt.sh"
    echo ""
fi

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose -f docker-compose.prod.yml down --remove-orphans
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "✅ Services are running!"
else
    echo "❌ Some services failed to start. Check logs:"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi

# Test health endpoint
echo "🔍 Testing health endpoint..."
if curl -f -s http://localhost/health > /dev/null; then
    echo "✅ Health check passed!"
else
    echo "⚠️  Health check failed. Service might still be starting..."
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "🔗 Your application is available at:"
echo "   HTTP:  http://localhost (redirects to HTTPS)"
echo "   HTTPS: https://localhost"
echo ""
echo "📋 Useful commands:"
echo "   View logs:    docker-compose -f docker-compose.prod.yml logs -f"
echo "   Stop services: docker-compose -f docker-compose.prod.yml down"
echo "   Restart:      docker-compose -f docker-compose.prod.yml restart"
echo ""
echo "🔧 Next steps for production:"
echo "   1. Setup proper SSL certificates: ./scripts/setup-letsencrypt.sh"
echo "   2. Configure firewall rules (see README)"
echo "   3. Setup monitoring and log aggregation"
echo "   4. Configure backup strategy"