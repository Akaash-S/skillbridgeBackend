#!/bin/bash

# Fixed domain setup script - handles port 80 conflict with Docker
set -e

echo "🌐 Setting up Domain: skillbridge-server.asolvitra.tech (Fixed)"
echo "============================================================="
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
    echo "Please run with: sudo ./domain-setup-fixed.sh"
    echo "Or ensure you have sudo privileges"
fi

# Check if we're in the right directory
if [ ! -f "Dockerfile" ] || [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the directory containing Dockerfile and docker-compose.yml"
    exit 1
fi

print_success "Found required files"

# Step 1: Stop Docker to free up port 80
echo "🛑 Stopping Docker to free up port 80..."
docker compose down 2>/dev/null || true
print_success "Docker stopped"

# Check if port 80 is still in use
if netstat -tuln | grep -q ":80 "; then
    print_warning "Port 80 is still in use by another process"
    echo "Processes using port 80:"
    sudo netstat -tulnp | grep ":80 "
    echo ""
    read -p "Do you want to continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "Port 80 is now free"
fi

# Step 2: Install Nginx
echo "📦 Installing Nginx..."
if command -v nginx &> /dev/null; then
    print_success "Nginx already installed"
else
    sudo apt update
    sudo apt install -y nginx
    print_success "Nginx installed"
fi

# Step 3: Install Certbot for Let's Encrypt
echo "🔐 Installing Certbot..."
if command -v certbot &> /dev/null; then
    print_success "Certbot already installed"
else
    sudo apt install -y certbot python3-certbot-nginx
    print_success "Certbot installed"
fi

# Step 4: Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow 'Nginx Full' 2>/dev/null || true
sudo ufw allow OpenSSH 2>/dev/null || true
sudo ufw --force enable 2>/dev/null || true
print_success "Firewall configured"

# Step 5: Create Nginx configuration
echo "⚙️  Creating Nginx configuration..."
sudo tee /etc/nginx/sites-available/skillbridge > /dev/null << 'EOF'
server {
    listen 80;
    server_name skillbridge-server.asolvitra.tech;

    # Allow Let's Encrypt challenges
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }

    # Proxy all other traffic to Docker container
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        
        # CORS headers for all responses
        add_header Access-Control-Allow-Origin "https://skillbridge.asolvitra.tech, https://www.skillbridge.asolvitra.tech, https://skillbridge.vercel.app" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Accept, Origin" always;
        add_header Access-Control-Allow-Credentials "true" always;
        
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
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

# Enable the site and disable default
sudo ln -sf /etc/nginx/sites-available/skillbridge /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
if sudo nginx -t; then
    print_success "Nginx configuration is valid"
else
    print_error "Nginx configuration is invalid"
    exit 1
fi

# Step 6: Start Nginx
echo "🚀 Starting Nginx..."
sudo systemctl enable nginx
sudo systemctl start nginx

if sudo systemctl is-active --quiet nginx; then
    print_success "Nginx is running"
else
    print_error "Failed to start Nginx"
    sudo systemctl status nginx
    exit 1
fi

# Step 7: Update docker-compose.yml to only use port 8000 internally
echo "🐳 Updating Docker configuration..."
cat > docker-compose.yml << 'EOF'
# Docker Compose file for SkillBridge Backend - Domain Setup (Fixed)

services:
  skillbridge:
    build: 
      context: .
      dockerfile: Dockerfile
    container_name: skillbridge-app
    ports:
      - "127.0.0.1:8000:8000"  # Only bind to localhost:8000
    environment:
      # Flask Configuration
      - SECRET_KEY=${SECRET_KEY}
      - FLASK_ENV=${FLASK_ENV:-production}
      
      # Production Port Configuration
      - PORT=${PORT:-8000}
      
      # Firebase Configuration
      - FIREBASE_SERVICE_ACCOUNT_BASE64=${FIREBASE_SERVICE_ACCOUNT_BASE64}
      - DISABLE_FIREBASE=${DISABLE_FIREBASE:-false}
      
      # Gemini AI Configuration
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - YOUTUBE_API_KEY=${YOUTUBE_API_KEY}
      
      # Adzuna Jobs API Configuration
      - ADZUNA_APP_ID=${ADZUNA_APP_ID}
      - ADZUNA_APP_KEY=${ADZUNA_APP_KEY}
      
      # MFA Configuration
      - MFA_ISSUER_NAME=${MFA_ISSUER_NAME}
      - MFA_SECRET_KEY=${MFA_SECRET_KEY}
      
      # SMTP Email Configuration
      - SMTP_HOST=${SMTP_HOST:-smtp.gmail.com}
      - SMTP_PORT=${SMTP_PORT:-587}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - SMTP_USE_TLS=${SMTP_USE_TLS:-true}
      
      # Email Settings
      - EMAIL_FROM_NAME=${EMAIL_FROM_NAME}
      - EMAIL_SUPPORT=${EMAIL_SUPPORT}
      - EMAIL_RATE_LIMIT=${EMAIL_RATE_LIMIT}
      - EMAIL_BATCH_SIZE=${EMAIL_BATCH_SIZE}
      
      # CORS Configuration
      - CORS_ORIGINS=${CORS_ORIGINS}
      
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

print_success "Docker configuration updated (port 8000 only)"

# Step 8: Start the application
echo "🔄 Starting application with new configuration..."
docker compose up -d

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 20

# Test local connection
if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    print_success "Application is running on localhost:8000"
else
    print_error "Application is not responding on localhost:8000"
    echo "Check logs: docker compose logs -f"
    exit 1
fi

# Step 9: Test Nginx proxy
echo "🔗 Testing Nginx proxy..."
if curl -f -s http://localhost/health > /dev/null 2>&1; then
    print_success "Nginx proxy is working"
else
    print_warning "Nginx proxy test failed, but this might be normal if domain DNS isn't set up yet"
fi

# Step 10: Check current server IP and DNS
echo "🌐 Checking DNS configuration..."
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo 'Unable to detect')
print_info "Your server IP: $SERVER_IP"

# Check if domain resolves to this server
DOMAIN_IP=$(nslookup $DOMAIN 2>/dev/null | grep -A1 "Name:" | tail -1 | awk '{print $2}' 2>/dev/null || echo "Not resolved")
print_info "Domain $DOMAIN resolves to: $DOMAIN_IP"

if [ "$SERVER_IP" = "$DOMAIN_IP" ]; then
    print_success "Domain correctly points to this server"
    DNS_READY=true
else
    print_warning "Domain does not point to this server yet"
    print_info "Please update your DNS A record:"
    echo "   Name: skillbridge-server"
    echo "   Type: A"
    echo "   Value: $SERVER_IP"
    echo "   TTL: 300"
    DNS_READY=false
fi

# Step 11: Obtain SSL certificate (only if DNS is ready)
if [ "$DNS_READY" = true ]; then
    echo "🔐 Obtaining SSL certificate from Let's Encrypt..."
    if sudo certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive; then
        print_success "SSL certificate obtained successfully"
        SSL_READY=true
    else
        print_warning "SSL certificate setup failed"
        print_info "You can try again later with:"
        echo "sudo certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos"
        SSL_READY=false
    fi
else
    print_info "Skipping SSL setup until DNS is configured"
    print_info "After DNS is set up, run:"
    echo "sudo certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos"
    SSL_READY=false
fi

# Step 12: Test the setup
echo "🧪 Testing the setup..."
sleep 5

# Test HTTP
if curl -f -s http://$DOMAIN/health > /dev/null 2>&1; then
    print_success "HTTP access working: http://$DOMAIN/health"
elif [ "$DNS_READY" = false ]; then
    print_info "HTTP test skipped (DNS not ready)"
else
    print_warning "HTTP access test failed"
fi

# Test HTTPS (if SSL was set up)
if [ "$SSL_READY" = true ]; then
    if curl -f -s https://$DOMAIN/health > /dev/null 2>&1; then
        print_success "HTTPS access working: https://$DOMAIN/health"
    else
        print_warning "HTTPS access not yet available (SSL may still be setting up)"
    fi
else
    print_info "HTTPS test skipped (SSL not set up yet)"
fi

echo ""
echo "🎉 Domain Setup Complete!"
echo "========================"
echo ""
echo "📊 Current Status:"
echo "   🐳 Docker: Running on localhost:8000"
echo "   🌐 Nginx: Running on port 80 (proxy to Docker)"
echo "   🔗 DNS: $([ "$DNS_READY" = true ] && echo "✅ Ready" || echo "⚠️  Needs configuration")"
echo "   🔒 SSL: $([ "$SSL_READY" = true ] && echo "✅ Active" || echo "⚠️  Pending DNS")"
echo ""

if [ "$DNS_READY" = true ] && [ "$SSL_READY" = true ]; then
    echo "🔗 Your SkillBridge backend is now available at:"
    echo "   🌐 Domain:   https://$DOMAIN"
    echo "   🔒 Secure:   https://$DOMAIN/health"
    echo "   📡 API:      https://$DOMAIN/api/..."
else
    echo "🔗 Your SkillBridge backend will be available at:"
    echo "   🌐 Domain:   https://$DOMAIN (after DNS + SSL setup)"
    echo "   🏠 Local:    http://localhost/health (working now)"
    echo "   🔧 Direct:   http://127.0.0.1:8000/health (working now)"
fi

echo ""
echo "📋 Architecture:"
echo "   Internet → Nginx (Port 80/443) → Docker (Port 8000) → Flask App"
echo ""
echo "📋 Management commands:"
echo "   🐳 Docker:   docker compose logs -f"
echo "   🌐 Nginx:    sudo systemctl status nginx"
echo "   🔐 SSL:      sudo certbot certificates"
echo "   🔄 Reload:   sudo systemctl reload nginx"
echo ""

# Set up automatic certificate renewal
if [ "$SSL_READY" = true ]; then
    echo "⚙️  Setting up automatic SSL certificate renewal..."
    if ! sudo crontab -l 2>/dev/null | grep -q certbot; then
        (sudo crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | sudo crontab -
        print_success "Automatic SSL renewal configured"
    else
        print_success "Automatic SSL renewal already configured"
    fi
fi

echo ""
if [ "$DNS_READY" = false ]; then
    echo "🔧 Next Steps:"
    echo "1. Update your DNS A record to point to: $SERVER_IP"
    echo "2. Wait for DNS propagation (5-30 minutes)"
    echo "3. Run: sudo certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos"
    echo "4. Test with: ./verify-domain.sh"
    echo ""
fi

echo "✅ Domain setup script completed!"
echo "Your SkillBridge backend is now properly configured! 🚀"