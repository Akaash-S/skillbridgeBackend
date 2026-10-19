#!/bin/bash

# GCP Compute Engine Deployment Script
# Single container deployment with Nginx + Gunicorn + Redis

set -e

echo "🚀 Deploying SkillBridge to GCP Compute Engine..."

# Check if required files exist
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it from .env.example"
    exit 1
fi

if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found"
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs nginx/ssl

# Load environment variables
source .env

# Generate SSL certificates if they don't exist
if [ ! -f "nginx/ssl/fullchain.pem" ]; then
    echo "🔐 Generating self-signed SSL certificates..."
    
    # Generate private key
    openssl genrsa -out nginx/ssl/privkey.pem 2048
    
    # Generate certificate
    openssl req -new -x509 -key nginx/ssl/privkey.pem -out nginx/ssl/fullchain.pem -days 365 \
        -subj "/C=US/ST=State/L=City/O=SkillBridge/CN=${DOMAIN:-localhost}"
    
    # Create chain file
    cp nginx/ssl/fullchain.pem nginx/ssl/chain.pem
    
    # Set permissions
    chmod 600 nginx/ssl/*.pem
    
    echo "✅ Self-signed certificates generated"
    echo "⚠️  For production, run: ./setup-letsencrypt-gcp.sh"
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down --remove-orphans 2>/dev/null || true

# Build and start the application
echo "🏗️  Building application..."
docker-compose build --no-cache

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

# Configure firewall rules
echo "🛡️  Configuring firewall rules..."

# Check if gcloud is available
if command -v gcloud &> /dev/null; then
    echo "🔧 Setting up GCP firewall rules..."
    
    # Allow HTTP and HTTPS
    gcloud compute firewall-rules create skillbridge-allow-web \
        --allow tcp:80,tcp:443 \
        --source-ranges 0.0.0.0/0 \
        --description "Allow HTTP and HTTPS for SkillBridge" \
        --quiet 2>/dev/null || echo "Firewall rule may already exist"
    
    # Block direct access to application ports
    gcloud compute firewall-rules create skillbridge-deny-direct \
        --action deny \
        --rules tcp:8080,tcp:6379 \
        --source-ranges 0.0.0.0/0 \
        --priority 1000 \
        --description "Block direct access to application ports" \
        --quiet 2>/dev/null || echo "Firewall rule may already exist"
    
    echo "✅ GCP firewall rules configured"
else
    echo "⚠️  gcloud CLI not found. Please configure firewall manually:"
    echo "   - Allow ports 80, 443 from 0.0.0.0/0"
    echo "   - Block ports 8080, 6379 from 0.0.0.0/0"
fi

# Check if UFW is available (Ubuntu/Debian)
if command -v ufw &> /dev/null; then
    echo "🔧 Configuring UFW firewall..."
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw deny 8080/tcp
    sudo ufw deny 6379/tcp
    echo "✅ UFW firewall configured"
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🔗 Your application is available at:"
echo "   HTTP:  http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP')"
echo "   HTTPS: https://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP')"
echo ""
echo "📋 Useful commands:"
echo "   View logs:    docker-compose logs -f"
echo "   Stop service: docker-compose down"
echo "   Restart:      docker-compose restart"
echo "   Monitor:      ./scripts/monitor-services.sh"
echo ""
echo "🔧 Next steps:"
echo "   1. Update DNS to point to this server"
echo "   2. Setup Let's Encrypt: ./setup-letsencrypt-gcp.sh"
echo "   3. Configure monitoring and backups"
echo "   4. Test your application thoroughly"
echo ""
echo "🔍 Health check: curl -f http://localhost/health"