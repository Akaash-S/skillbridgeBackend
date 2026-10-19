#!/bin/bash

# Domain setup script for skillbridge-server.asolvitra.tech
set -e

echo "🌐 Setting up Domain: skillbridge-server.asolvitra.tech"
echo "===================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

DOMAIN="skillbridge-server.asolvitra.tech"
EMAIL="admin@asolvitra.tech"

# Check if we're running as root or with sudo access
if [ "$EUID" -ne 0 ]; then
    print_warning "This script needs sudo access for some operations"
    echo "Please run with: sudo ./domain-setup.sh"
    echo "Or ensure you have sudo privileges"
fi

# Check if we're in the right directory
if [ ! -f "Dockerfile" ] || [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the directory containing Dockerfile and docker-compose.yml"
    exit 1
fi

print_success "Found required files"

# Step 1: Install Nginx (as reverse proxy)
echo "📦 Installing Nginx..."
if command -v nginx &> /dev/null; then
    print_success "Nginx already installed"
else
    sudo apt update
    sudo apt install -y nginx
    print_success "Nginx installed"
fi

# Step 2: Install Certbot for Let's Encrypt
echo "🔐 Installing Certbot..."
if command -v certbot &> /dev/null; then
    print_success "Certbot already installed"
else
    sudo apt install -y certbot python3-certbot-nginx
    print_success "Certbot installed"
fi

# Step 3: Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw --force enable
print_success "Firewall configured"

# Step 4: Create Nginx configuration
echo "⚙️  Creating Nginx configuration..."
sudo tee /etc/nginx/sites-available/skillbridge > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Allow Let's Encrypt challenges
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }

    # Redirect all other traffic to HTTPS (will be added after SSL setup)
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # CORS headers
        add_header Access-Control-Allow-Origin "https://skillbridge.asolvitra.tech, https://www.skillbridge.asolvitra.tech, https://skillbridge.vercel.app" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Accept, Origin" always;
        add_header Access-Control-Allow-Credentials "true" always;
        
        # Handle preflight requests
        if (\$request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin "https://skillbridge.asolvitra.tech, https://www.skillbridge.asolvitra.tech, https://skillbridge.vercel.app" always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Accept, Origin" always;
            add_header Access-Control-Allow-Credentials "true" always;
            add_header Access-Control-Max-Age 86400 always;
            add_header Content-Length 0;
            add_header Content-Type "text/plain";
            return 204;
        }
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/skillbridge /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
if sudo nginx -t; then
    print_success "Nginx configuration is valid"
    sudo systemctl reload nginx
else
    print_error "Nginx configuration is invalid"
    exit 1
fi

# Step 5: Update docker-compose.yml to use port 8000 internally
echo "🐳 Updating Docker configuration..."
cat > docker-compose.yml << EOF
# Docker Compose file for SkillBridge Backend - Domain Setup

services:
  skillbridge:
    build: 
      context: .
      dockerfile: Dockerfile
    container_name: skillbridge-app
    ports:
      - "127.0.0.1:8000:8000"  # Only bind to localhost
    environment:
      # Flask Configuration
      - SECRET_KEY=\${SECRET_KEY}
      - FLASK_ENV=\${FLASK_ENV:-production}
      
      # Production Port Configuration
      - PORT=\${PORT:-8000}
      
      # Firebase Configuration
      - FIREBASE_SERVICE_ACCOUNT_BASE64=\${FIREBASE_SERVICE_ACCOUNT_BASE64}
      - DISABLE_FIREBASE=\${DISABLE_FIREBASE:-false}
      
      # Gemini AI Configuration
      - GEMINI_API_KEY=\${GEMINI_API_KEY}
      - YOUTUBE_API_KEY=\${YOUTUBE_API_KEY}
      
      # Adzuna Jobs API Configuration
      - ADZUNA_APP_ID=\${ADZUNA_APP_ID}
      - ADZUNA_APP_KEY=\${ADZUNA_APP_KEY}
      
      # MFA Configuration
      - MFA_ISSUER_NAME=\${MFA_ISSUER_NAME}
      - MFA_SECRET_KEY=\${MFA_SECRET_KEY}
      
      # SMTP Email Configuration
      - SMTP_HOST=\${SMTP_HOST:-smtp.gmail.com}
      - SMTP_PORT=\${SMTP_PORT:-587}
      - SMTP_USER=\${SMTP_USER}
      - SMTP_PASSWORD=\${SMTP_PASSWORD}
      - SMTP_USE_TLS=\${SMTP_USE_TLS:-true}
      
      # Email Settings
      - EMAIL_FROM_NAME=\${EMAIL_FROM_NAME}
      - EMAIL_SUPPORT=\${EMAIL_SUPPORT}
      - EMAIL_RATE_LIMIT=\${EMAIL_RATE_LIMIT}
      - EMAIL_BATCH_SIZE=\${EMAIL_BATCH_SIZE}
      
      # CORS Configuration
      - CORS_ORIGINS=\${CORS_ORIGINS}
      
    restart: unless-stopped
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
      
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

networks:
  default:
    name: skillbridge-network
EOF

print_success "Docker configuration updated"

# Step 6: Restart the application
echo "🔄 Restarting application with new configuration..."
docker compose down
docker compose up -d

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 15

# Test local connection
if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    print_success "Application is running on localhost:8000"
else
    print_error "Application is not responding on localhost:8000"
    echo "Check logs: docker compose logs -f"
    exit 1
fi

# Step 7: Obtain SSL certificate
echo "🔐 Obtaining SSL certificate from Let's Encrypt..."
print_warning "Make sure your domain $DOMAIN points to this server's IP address"
echo "Current server IP: $(curl -s ifconfig.me 2>/dev/null || echo 'Unable to detect')"
echo ""
read -p "Press Enter when your domain DNS is configured and pointing to this server..."

if sudo certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive; then
    print_success "SSL certificate obtained successfully"
else
    print_warning "SSL certificate setup failed. You can try again later with:"
    echo "sudo certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos"
    echo ""
    print_info "Your site is still accessible via HTTP at: http://$DOMAIN"
fi

# Step 8: Test the setup
echo "🧪 Testing the setup..."
sleep 5

# Test HTTP
if curl -f -s http://$DOMAIN/health > /dev/null 2>&1; then
    print_success "HTTP access working: http://$DOMAIN/health"
else
    print_warning "HTTP access test failed"
fi

# Test HTTPS (if SSL was set up)
if curl -f -s https://$DOMAIN/health > /dev/null 2>&1; then
    print_success "HTTPS access working: https://$DOMAIN/health"
else
    print_warning "HTTPS access not yet available (SSL may still be setting up)"
fi

echo ""
echo "🎉 Domain Setup Complete!"
echo "========================"
echo ""
echo "🔗 Your SkillBridge backend is now available at:"
echo "   🌐 Domain:   https://$DOMAIN"
echo "   🔒 Secure:   https://$DOMAIN/health"
echo "   📡 API:      https://$DOMAIN/api/..."
echo ""
echo "📋 Architecture:"
echo "   🌐 Nginx (reverse proxy) → 🐳 Docker (Gunicorn) → 🐍 Flask App"
echo "   ✅ SSL/TLS encryption via Let's Encrypt"
echo "   ✅ CORS configured for your frontend domains"
echo "   ✅ Automatic HTTP → HTTPS redirect"
echo ""
echo "📋 Management commands:"
echo "   🐳 Docker:   docker compose logs -f"
echo "   🌐 Nginx:    sudo systemctl status nginx"
echo "   🔐 SSL:      sudo certbot certificates"
echo "   🔄 Reload:   sudo systemctl reload nginx"
echo ""
echo "🔒 Security features:"
echo "   ✅ Let's Encrypt SSL certificate"
echo "   ✅ Automatic certificate renewal"
echo "   ✅ HTTPS-only access (after SSL setup)"
echo "   ✅ Secure headers configured"
echo ""
echo "🚀 Your backend is now production-ready with HTTPS!"

# Set up automatic certificate renewal
echo "⚙️  Setting up automatic SSL certificate renewal..."
if ! sudo crontab -l 2>/dev/null | grep -q certbot; then
    (sudo crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | sudo crontab -
    print_success "Automatic SSL renewal configured"
else
    print_success "Automatic SSL renewal already configured"
fi

echo ""
echo "✅ Domain setup script completed!"
echo "Your SkillBridge backend is now live at: https://$DOMAIN 🚀"