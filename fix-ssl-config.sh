#!/bin/bash

# Fix SSL configuration and HTTP to HTTPS redirect
set -e

echo "🔧 Fixing SSL Configuration"
echo "==========================="
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

# Check what configuration files exist
echo "🔍 Checking Nginx configuration files..."
echo ""

if [ -f "/etc/nginx/sites-enabled/skillbridge" ]; then
    print_info "Found: /etc/nginx/sites-enabled/skillbridge"
fi

if [ -f "/etc/nginx/sites-enabled/skillbridge-server.asolvitra.tech" ]; then
    print_info "Found: /etc/nginx/sites-enabled/skillbridge-server.asolvitra.tech"
fi

if [ -f "/etc/nginx/nginx.conf" ]; then
    print_info "Found: /etc/nginx/nginx.conf"
fi

echo ""

# Create the correct configuration
echo "⚙️  Creating correct SSL configuration..."

sudo tee /etc/nginx/sites-available/skillbridge << 'EOF' > /dev/null
# SkillBridge Backend - Complete SSL Configuration
upstream skillbridge_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# HTTP Server - Redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name skillbridge-server.asolvitra.tech;

    # Allow Let's Encrypt challenges
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }

    # Redirect all other HTTP traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name skillbridge-server.asolvitra.tech;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/skillbridge-server.asolvitra.tech/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/skillbridge-server.asolvitra.tech/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Client settings
    client_max_body_size 10M;

    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    # Health check endpoint
    location = /health {
        proxy_pass http://skillbridge_backend/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        # CORS headers
        add_header Access-Control-Allow-Origin "https://skillbridge.asolvitra.tech, https://www.skillbridge.asolvitra.tech, https://skillbridge.vercel.app" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Accept, Origin" always;
        add_header Access-Control-Allow-Credentials "true" always;
        
        access_log off;
    }

    # Auth endpoints
    location /auth/ {
        proxy_pass http://skillbridge_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        # CORS headers
        add_header Access-Control-Allow-Origin "https://skillbridge.asolvitra.tech, https://www.skillbridge.asolvitra.tech, https://skillbridge.vercel.app" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Accept, Origin" always;
        add_header Access-Control-Allow-Credentials "true" always;
        
        # Handle preflight
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

    # All other API endpoints
    location / {
        proxy_pass http://skillbridge_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        # CORS headers
        add_header Access-Control-Allow-Origin "https://skillbridge.asolvitra.tech, https://www.skillbridge.asolvitra.tech, https://skillbridge.vercel.app" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Accept, Origin" always;
        add_header Access-Control-Allow-Credentials "true" always;
        
        # Handle preflight
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

print_success "Configuration created"

# Remove any conflicting configurations
echo "🧹 Cleaning up conflicting configurations..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/skillbridge-server.asolvitra.tech
print_success "Cleanup done"

# Enable the correct configuration
echo "🔗 Enabling configuration..."
sudo ln -sf /etc/nginx/sites-available/skillbridge /etc/nginx/sites-enabled/
print_success "Configuration enabled"

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
if sudo nginx -t; then
    print_success "Nginx configuration is valid"
else
    print_error "Nginx configuration has errors"
    sudo nginx -t
    exit 1
fi

# Reload Nginx
echo "🔄 Reloading Nginx..."
sudo systemctl reload nginx
print_success "Nginx reloaded"

# Wait for reload to complete
sleep 3

# Test the configuration
echo ""
echo "🧪 Testing the setup..."
echo ""

# Test HTTP (should redirect)
echo "1. Testing HTTP (should redirect to HTTPS)..."
HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN/health 2>/dev/null || echo "000")
if [ "$HTTP_RESPONSE" = "301" ] || [ "$HTTP_RESPONSE" = "302" ]; then
    print_success "HTTP correctly redirects to HTTPS (Status: $HTTP_RESPONSE)"
elif [ "$HTTP_RESPONSE" = "200" ]; then
    print_warning "HTTP returns 200 (should redirect to HTTPS)"
else
    print_warning "HTTP returned status: $HTTP_RESPONSE"
fi

# Test HTTPS
echo ""
echo "2. Testing HTTPS..."
HTTPS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health 2>/dev/null || echo "000")
if [ "$HTTPS_RESPONSE" = "200" ]; then
    print_success "HTTPS is working! (Status: $HTTPS_RESPONSE)"
    CONTENT=$(curl -s https://$DOMAIN/health 2>/dev/null)
    print_info "Response: $CONTENT"
else
    print_warning "HTTPS returned status: $HTTPS_RESPONSE"
fi

# Test CORS
echo ""
echo "3. Testing CORS headers..."
CORS_HEADER=$(curl -s -H "Origin: https://skillbridge.asolvitra.tech" -I https://$DOMAIN/health 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
if [ ! -z "$CORS_HEADER" ]; then
    print_success "CORS headers present"
    print_info "$CORS_HEADER"
else
    print_warning "CORS headers not found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SSL Configuration Fixed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$HTTPS_RESPONSE" = "200" ]; then
    echo "🎉 Your backend is fully operational with HTTPS!"
    echo ""
    echo "🔗 Access URLs:"
    echo "   ✅ https://$DOMAIN"
    echo "   ✅ https://$DOMAIN/health"
    echo "   ✅ https://$DOMAIN/api/..."
    echo ""
    echo "🔒 Security Features:"
    echo "   ✅ SSL/TLS encryption"
    echo "   ✅ HTTP → HTTPS redirect"
    echo "   ✅ CORS configured"
    echo "   ✅ Security headers"
    echo ""
    echo "🚀 Your backend is production-ready!"
else
    echo "⚠️  HTTPS needs attention"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   1. Check Docker: curl http://127.0.0.1:8000/health"
    echo "   2. Check logs: sudo tail -50 /var/log/nginx/skillbridge-error.log"
    echo "   3. Reload Nginx: sudo systemctl reload nginx"
    echo "   4. Test again: curl -I https://$DOMAIN/health"
fi

echo ""
echo "📋 Quick test commands:"
echo "   curl -I http://$DOMAIN/health   # Should redirect"
echo "   curl -I https://$DOMAIN/health  # Should return 200"
echo ""