#!/bin/bash

# Simple build and run script for GCP Compute Engine
# Run this script on your GCP instance after cloning the repository

set -e

echo "🚀 Building and running SkillBridge on GCP..."

# Check if we're in the right directory
if [ ! -f "Dockerfile" ] || [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the backend directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Creating from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️  Please edit .env file with your actual configuration before continuing"
        echo "   nano .env"
        read -p "Press Enter after editing .env file..."
    else
        echo "❌ .env.example not found. Please create .env file manually"
        exit 1
    fi
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs nginx/ssl

# Generate SSL certificates if they don't exist
if [ ! -f "nginx/ssl/fullchain.pem" ]; then
    echo "🔐 Generating self-signed SSL certificates..."
    
    # Get domain from .env file or use localhost
    DOMAIN=$(grep "^DOMAIN=" .env | cut -d'=' -f2 | tr -d '"' || echo "localhost")
    
    openssl genrsa -out nginx/ssl/privkey.pem 2048
    openssl req -new -x509 -key nginx/ssl/privkey.pem -out nginx/ssl/fullchain.pem -days 365 \
        -subj "/C=US/ST=State/L=City/O=SkillBridge/CN=$DOMAIN"
    cp nginx/ssl/fullchain.pem nginx/ssl/chain.pem
    chmod 600 nginx/ssl/*.pem
    
    echo "✅ Self-signed certificates generated for $DOMAIN"
    echo "⚠️  For production, run: ./setup-letsencrypt-gcp.sh after DNS is configured"
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down --remove-orphans 2>/dev/null || true

# Build the application
echo "🏗️  Building Docker image..."
docker-compose build --no-cache

# Start the application
echo "🚀 Starting application..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 15

# Check service health
echo "🏥 Checking service health..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s http://localhost/health > /dev/null 2>&1; then
        echo "✅ Health check passed!"
        break
    else
        echo "⏳ Waiting for service to be ready... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 2
        RETRY_COUNT=$((RETRY_COUNT + 1))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Health check failed after $MAX_RETRIES attempts"
    echo "📋 Container logs:"
    docker-compose logs --tail=50
    exit 1
fi

# Configure UFW firewall if available
if command -v ufw &> /dev/null; then
    echo "🛡️  Configuring UFW firewall..."
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw deny 8080/tcp
    sudo ufw deny 6379/tcp
    echo "✅ UFW firewall configured"
fi

# Show status
echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🔗 Your application is available at:"
echo "   HTTP:  http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')"
echo "   HTTPS: https://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')"
echo ""
echo "📋 Useful commands:"
echo "   View logs:    docker-compose logs -f"
echo "   Stop service: docker-compose down"
echo "   Restart:      docker-compose restart"
echo "   Check health: curl -f http://localhost/health"
echo ""
echo "🔧 Next steps:"
echo "   1. Configure your domain DNS to point to this server"
echo "   2. Setup Let's Encrypt SSL: ./setup-letsencrypt-gcp.sh"
echo "   3. Test your application thoroughly"
echo ""
echo "⚠️  Remember to:"
echo "   - Keep your .env file secure and never commit it to git"
echo "   - Setup monitoring and backups"
echo "   - Review security settings regularly"