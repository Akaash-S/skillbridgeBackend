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

# Create environment file template
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

echo ""
echo "🔧 CONFIGURATION REQUIRED!"
echo "=========================================="
echo ""
echo "📝 A template .env file has been created at:"
echo "   /opt/skillbridge/backend/.env"
echo ""
echo "⚠️  IMPORTANT: You MUST edit this file with your actual configuration!"
echo ""
echo "📋 Required steps:"
echo "   1. Open the .env file: nano .env"
echo "   2. Replace ALL placeholder values with your actual:"
echo "      - SECRET_KEY (generate a secure random key)"
echo "      - DOMAIN (your actual domain name)"
echo "      - SSL_EMAIL (your email for SSL certificates)"
echo "      - FIREBASE_SERVICE_ACCOUNT_BASE64 (from Firebase Console)"
echo "      - API keys (Gemini, YouTube, Adzuna, etc.)"
echo "      - Email settings (SMTP credentials)"
echo "      - REDIS_PASSWORD (secure password)"
echo "      - CORS_ORIGINS (your frontend domain)"
echo "   3. Save and exit (Ctrl+X, then Y, then Enter)"
echo "   4. Run the continuation script: ./continue-deployment.sh"
echo ""
echo "💡 Tip: You can also edit the file using vim or any text editor you prefer"
echo ""

# Create continuation script
cat > continue-deployment.sh << 'CONTINUE_EOF'
#!/bin/bash

# Continuation of GCP deployment after .env configuration
# This script runs after the user has configured their .env file

set -e

echo "🚀 Continuing SkillBridge deployment..."
echo ""

# Verify .env file has been configured
if grep -q "your-super-secret-key-change-this-in-production" .env; then
    echo "❌ ERROR: .env file still contains placeholder values!"
    echo "   Please edit .env file with your actual configuration first."
    echo "   Run: nano .env"
    exit 1
fi

if grep -q "your-domain.com" .env; then
    echo "❌ ERROR: Please update DOMAIN in .env file with your actual domain"
    echo "   Run: nano .env"
    exit 1
fi

echo "✅ .env file appears to be configured"
echo ""

# Create necessary directories
mkdir -p logs nginx/ssl

# Generate self-signed SSL certificates for initial setup
if [ ! -f "nginx/ssl/fullchain.pem" ]; then
    echo "🔐 Generating self-signed SSL certificates..."
    
    # Get domain from .env file or use localhost
    DOMAIN=$(grep "^DOMAIN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "localhost")
    if [ "$DOMAIN" = "your-domain.com" ] || [ -z "$DOMAIN" ]; then
        DOMAIN="localhost"
    fi
    
    openssl genrsa -out nginx/ssl/privkey.pem 2048
    openssl req -new -x509 -key nginx/ssl/privkey.pem -out nginx/ssl/fullchain.pem -days 365 \
        -subj "/C=US/ST=State/L=City/O=SkillBridge/CN=$DOMAIN"
    cp nginx/ssl/fullchain.pem nginx/ssl/chain.pem
    chmod 600 nginx/ssl/*.pem
    
    echo "✅ Self-signed certificates generated for $DOMAIN"
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
echo "🔧 Setting up GCP firewall rules..."
gcloud compute firewall-rules create skillbridge-allow-web \
    --allow tcp:80,tcp:443 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow HTTP and HTTPS for SkillBridge" \
    --quiet 2>/dev/null || echo "Web firewall rule may already exist"

gcloud compute firewall-rules create skillbridge-deny-direct \
    --action deny \
    --rules tcp:8080,tcp:6379 \
    --source-ranges 0.0.0.0/0 \
    --priority 1000 \
    --description "Block direct access to application ports" \
    --quiet 2>/dev/null || echo "Deny firewall rule may already exist"

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Check health
echo "🏥 Checking application health..."
MAX_RETRIES=20
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s http://localhost/health > /dev/null 2>&1; then
        echo "✅ Application is running successfully!"
        break
    else
        echo "⏳ Waiting for service to be ready... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 3
        RETRY_COUNT=$((RETRY_COUNT + 1))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "⚠️  Health check timeout. Application may still be starting."
    echo "📋 Check logs with: docker-compose logs"
else
    echo "🎉 Application deployed successfully!"
fi

# Get server IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "YOUR_SERVER_IP")

echo ""
echo "🎉 DEPLOYMENT COMPLETED!"
echo "=========================================="
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🔗 Your application is available at:"
echo "   HTTP:  http://$SERVER_IP"
echo "   HTTPS: https://$SERVER_IP (with self-signed certificate)"
echo ""
echo "🔧 Next steps:"
echo "   1. Configure your domain DNS to point to: $SERVER_IP"
echo "   2. Setup Let's Encrypt SSL: ./setup-letsencrypt-gcp.sh"
echo "   3. Test your application: curl -f http://$SERVER_IP/health"
echo ""
echo "📋 Useful commands:"
echo "   View logs:    docker-compose logs -f"
echo "   Stop service: docker-compose down"
echo "   Restart:      docker-compose restart"
echo "   Check health: curl -f http://localhost/health"
echo ""
echo "🔍 Troubleshooting:"
echo "   If health check fails, check logs: docker-compose logs"
echo "   If containers won't start, check .env file: cat .env"
echo ""
CONTINUE_EOF

# Make continuation script executable
chmod +x continue-deployment.sh

echo "📜 Created continuation script: continue-deployment.sh"
echo ""
echo "🚀 TO CONTINUE DEPLOYMENT:"
echo "   1. Edit your configuration: nano .env"
echo "   2. Run continuation script: ./continue-deployment.sh"
echo ""
echo "⏹️  Startup script paused. Please configure your .env file and run the continuation script."