#!/bin/bash

# GCP Compute Engine Startup Script
# This script will run when the instance starts up

set -e

echo "🚀 Starting SkillBridge deployment on GCP Compute Engine..."

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $(whoami)
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Create application directory
mkdir -p /opt/skillbridge
cd /opt/skillbridge

# Clone repository (replace with your repository URL)
if [ ! -d ".git" ]; then
    git clone https://github.com/Akaash-S/skillbridgeBackend.git .
fi

# Navigate to backend directory
cd backend

# Create environment file (you'll need to customize this)
cat > .env << 'EOF'
# Application Settings
SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=production
PORT=8080

# Domain Configuration (update with your domain)
DOMAIN=your-domain.com
SSL_EMAIL=admin@your-domain.com

# Firebase Configuration
FIREBASE_SERVICE_ACCOUNT_BASE64=your-base64-encoded-service-account
DISABLE_FIREBASE=false

# API Keys (add your actual keys)
GEMINI_API_KEY=your-gemini-api-key
YOUTUBE_API_KEY=your-youtube-api-key
ADZUNA_APP_ID=your-adzuna-app-id
ADZUNA_APP_KEY=your-adzuna-app-key

# MFA Configuration
MFA_ISSUER_NAME=SkillBridge
MFA_SECRET_KEY=your-mfa-secret-key

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
EMAIL_FROM_NAME=SkillBridge
EMAIL_SUPPORT=support@your-domain.com

# CORS Configuration
CORS_ORIGINS=https://your-frontend-domain.com

# Redis Configuration
REDIS_PASSWORD=secure-redis-password-change-this

# GCP Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GCP_REGION=us-central1
EOF

echo "⚠️  IMPORTANT: Please edit /opt/skillbridge/backend/.env with your actual configuration!"

# Create necessary directories
mkdir -p logs nginx/ssl

# Generate self-signed SSL certificates for initial setup
if [ ! -f "nginx/ssl/fullchain.pem" ]; then
    echo "🔐 Generating self-signed SSL certificates..."
    openssl genrsa -out nginx/ssl/privkey.pem 2048
    openssl req -new -x509 -key nginx/ssl/privkey.pem -out nginx/ssl/fullchain.pem -days 365 \
        -subj "/C=US/ST=State/L=City/O=SkillBridge/CN=localhost"
    cp nginx/ssl/fullchain.pem nginx/ssl/chain.pem
    chmod 600 nginx/ssl/*.pem
fi

# Build and start the application
echo "🏗️  Building and starting application..."
docker-compose build --no-cache
docker-compose up -d

# Configure firewall
echo "🛡️  Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw deny 8080/tcp
ufw deny 6379/tcp
ufw --force enable

# Setup GCP firewall rules
gcloud compute firewall-rules create skillbridge-allow-web \
    --allow tcp:80,tcp:443 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow HTTP and HTTPS for SkillBridge" \
    --quiet 2>/dev/null || echo "Firewall rule may already exist"

gcloud compute firewall-rules create skillbridge-deny-direct \
    --action deny \
    --rules tcp:8080,tcp:6379 \
    --source-ranges 0.0.0.0/0 \
    --priority 1000 \
    --description "Block direct access to application ports" \
    --quiet 2>/dev/null || echo "Firewall rule may already exist"

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Check health
if curl -f -s http://localhost/health > /dev/null 2>&1; then
    echo "✅ Application is running successfully!"
else
    echo "⚠️  Application may still be starting. Check logs with: docker-compose logs"
fi

echo ""
echo "🎉 Deployment completed!"
echo ""
echo "📋 Next steps:"
echo "1. Edit /opt/skillbridge/backend/.env with your actual configuration"
echo "2. Restart the application: cd /opt/skillbridge/backend && docker-compose restart"
echo "3. Configure your domain DNS to point to this server"
echo "4. Setup Let's Encrypt SSL: ./setup-letsencrypt-gcp.sh"
echo ""
echo "🔗 Your application will be available at:"
echo "   HTTP:  http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')"
echo "   HTTPS: https://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')"