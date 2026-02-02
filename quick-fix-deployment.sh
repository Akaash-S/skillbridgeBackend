#!/bin/bash

# Quick fix script for GCP deployment
# Run this if the startup script failed to find the backend directory

set -e

echo "🔧 SkillBridge Deployment Quick Fix"
echo "=================================="
echo ""

# Find the application directory
APP_DIR=""
SEARCH_DIRS=(
    "/opt/skillbridge"
    "/opt/skillbridge/backend"
    "/home/$(whoami)"
    "/home/$(whoami)/skillbridge"
    "/home/$(whoami)/skillbridge/backend"
    "/home/$(whoami)/skillbridgeBackend"
    "/home/$(whoami)/skillbridgeBackend/backend"
)

echo "🔍 Searching for application files..."
for dir in "${SEARCH_DIRS[@]}"; do
    if [ -d "$dir" ] && [ -f "$dir/Dockerfile" ] && [ -f "$dir/docker-compose.yml" ]; then
        APP_DIR="$dir"
        echo "✅ Found application at: $APP_DIR"
        break
    fi
done

if [ -z "$APP_DIR" ]; then
    echo "❌ Could not find application files. Let's set it up manually..."
    
    # Create directory and clone repository
    sudo mkdir -p /opt/skillbridge
    cd /opt/skillbridge
    
    if [ ! -d ".git" ]; then
        echo "📥 Cloning repository..."
        sudo git clone https://github.com/Akaash-S/skillbridgeBackend.git .
    fi
    
    # Check if files are in backend subdirectory or root
    if [ -d "backend" ] && [ -f "backend/Dockerfile" ]; then
        APP_DIR="/opt/skillbridge/backend"
        cd backend
    elif [ -f "Dockerfile" ]; then
        APP_DIR="/opt/skillbridge"
    else
        echo "❌ Repository structure is unexpected. Please check manually."
        ls -la
        exit 1
    fi
    
    echo "✅ Application set up at: $APP_DIR"
fi

# Navigate to application directory
cd "$APP_DIR"
echo "📍 Working in: $(pwd)"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env template..."
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
fi

# Create continuation script if it doesn't exist
if [ ! -f "continue-deployment.sh" ]; then
    echo "📜 Creating continuation script..."
    cat > continue-deployment.sh << 'CONTINUE_EOF'
#!/bin/bash

# Continuation of GCP deployment after .env configuration

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
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8080/tcp
sudo ufw deny 6379/tcp

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
CONTINUE_EOF

    chmod +x continue-deployment.sh
fi

# Create edit helper script
if [ ! -f "edit-config.sh" ]; then
    echo "📝 Creating configuration helper..."
    cat > edit-config.sh << 'EDIT_EOF'
#!/bin/bash

echo "🔧 Opening .env configuration file..."
echo ""
echo "📝 Please update the following required values:"
echo "   - SECRET_KEY (generate a secure random key)"
echo "   - DOMAIN (your actual domain name)"
echo "   - SSL_EMAIL (your email for SSL certificates)"
echo "   - FIREBASE_SERVICE_ACCOUNT_BASE64"
echo "   - API keys (Gemini, YouTube, etc.)"
echo "   - Email settings (SMTP credentials)"
echo "   - REDIS_PASSWORD"
echo "   - CORS_ORIGINS (your frontend domain)"
echo ""
echo "💡 Tip: Use Ctrl+X, then Y, then Enter to save and exit"
echo ""
read -p "Press Enter to open the .env file for editing..."

nano .env

echo ""
echo "✅ Configuration file updated!"
echo ""
echo "🚀 Next steps:"
echo "   1. Run the continuation script: ./continue-deployment.sh"
echo ""
EDIT_EOF

    chmod +x edit-config.sh
fi

echo ""
echo "🎉 Quick fix completed!"
echo "======================"
echo ""
echo "📍 Application directory: $APP_DIR"
echo "📝 Configuration file: $APP_DIR/.env"
echo ""
echo "🚀 Next steps:"
echo "   1. Edit your configuration: nano .env (or ./edit-config.sh)"
echo "   2. Run deployment: ./continue-deployment.sh"
echo ""
echo "📋 Files available:"
ls -la | grep -E "(\.env|continue-deployment|edit-config|docker-compose|Dockerfile)"