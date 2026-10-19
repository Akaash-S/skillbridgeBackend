#!/bin/bash

# Fix Nginx proxy configuration to properly connect to Docker
set -e

echo "🔧 Fixing Nginx Proxy Configuration"
echo "===================================="
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

# Check if Docker is running
echo "🐳 Checking Docker status..."
if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    print_success "Docker container is responding on localhost:8000"
else
    print_error "Docker container is not responding on localhost:8000"
    echo "Starting Docker..."
    docker compose up -d
    sleep 15
    
    if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        print_success "Docker container is now responding"
    else
        print_error "Docker container still not responding"
        echo "Check logs: docker compose logs -f"
        exit 1
    fi
fi

# Create proper Nginx configuration
echo "⚙️  Creating proper Nginx configuration..."
sudo tee /etc/nginx/sites-available/skillbridge > /dev/null << 'EOF'
# SkillBridge Backend Nginx Configuration
upstream skillbridge_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name skillbridge-server.asolvitra.tech;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Allow Let's Encrypt challenges
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }

    # Proxy all traffic to Docker container
    location / {
        proxy_pass http://skillbridge_backend;
        proxy_http_version 1.1;
        
        # Essential proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header Connection "";
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        
        # CORS headers
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
            add_header Content-Type "text/plain charset=UTF-8";
            return 204;
        }
    }

    # Logging
    access_log /var/log/nginx/skillbridge-access.log;
    error_log /var/log/nginx/skillbridge-error.log;
}
EOF

print_success "Nginx configuration created"

# Enable the site
echo "🔗 Enabling site..."
sudo ln -sf /etc/nginx/sites-available/skillbridge /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
if sudo nginx -t; then
    print_success "Nginx configuration is valid"
else
    print_error "Nginx configuration is invalid"
    sudo nginx -t
    exit 1
fi

# Reload Nginx
echo "🔄 Reloading Nginx..."
sudo systemctl reload nginx

if sudo systemctl is-active --quiet nginx; then
    print_success "Nginx reloaded successfully"
else
    print_error "Nginx failed to reload"
    sudo systemctl status nginx
    exit 1
fi

# Wait a moment for Nginx to fully reload
sleep 3

# Test the proxy
echo "🧪 Testing Nginx proxy..."
echo ""

# Test 1: Direct Docker access
print_info "Test 1: Direct Docker access"
if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    print_success "Docker responds on localhost:8000"
else
    print_error "Docker not responding on localhost:8000"
fi

# Test 2: Nginx proxy via localhost
print_info "Test 2: Nginx proxy via localhost"
RESPONSE=$(curl -s http://localhost/health 2>&1)
if echo "$RESPONSE" | grep -q "status\|health\|ok" 2>/dev/null; then
    print_success "Nginx proxy working via localhost"
    print_info "Response: $RESPONSE"
else
    print_warning "Nginx proxy test via localhost failed"
    echo "Response: $RESPONSE"
fi

# Test 3: Nginx proxy via domain
print_info "Test 3: Nginx proxy via domain"
RESPONSE=$(curl -s http://$DOMAIN/health 2>&1)
if echo "$RESPONSE" | grep -q "status\|health\|ok" 2>/dev/null; then
    print_success "Nginx proxy working via domain"
    print_info "Response: $RESPONSE"
else
    print_warning "Nginx proxy test via domain failed"
    echo "Response: $RESPONSE"
fi

# Check Nginx error logs for issues
echo ""
echo "📋 Recent Nginx error logs:"
sudo tail -20 /var/log/nginx/skillbridge-error.log 2>/dev/null || echo "No errors logged yet"

echo ""
echo "📋 Recent Nginx access logs:"
sudo tail -10 /var/log/nginx/skillbridge-access.log 2>/dev/null || echo "No access logged yet"

echo ""
echo "✅ Nginx proxy configuration fixed!"
echo ""
echo "🔗 Test your setup:"
echo "   curl http://localhost/health"
echo "   curl http://$DOMAIN/health"
echo ""
echo "🚀 Next step: Set up SSL with:"
echo "   sudo certbot --nginx -d $DOMAIN --email admin@asolvitra.tech --agree-tos"
echo ""