#!/bin/bash

# Fix CORS headers - Access-Control-Allow-Origin can only have one value
set -e

echo "🔧 Fixing CORS Headers"
echo "======================"
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

echo "⚙️  Creating correct CORS configuration..."
echo "Note: Access-Control-Allow-Origin can only have ONE value"
echo ""

# Create the correct configuration with proper CORS handling
sudo tee /etc/nginx/sites-available/skillbridge << 'EOF' > /dev/null
# SkillBridge Backend - Correct CORS Configuration
upstream skillbridge_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# Map to set CORS origin dynamically
map $http_origin $cors_origin {
    default "";
    "~^https://skillbridge\.asolvitra\.tech$" $http_origin;
    "~^https://www\.skillbridge\.asolvitra\.tech$" $http_origin;
    "~^https://skillbridge\.vercel\.app$" $http_origin;
    "~^http://localhost:[0-9]+$" $http_origin;
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
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin $cors_origin always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Accept, Origin" always;
            add_header Access-Control-Allow-Credentials "true" always;
            add_header Access-Control-Max-Age 86400 always;
            add_header Content-Length 0;
            add_header Content-Type "text/plain charset=UTF-8";
            return 204;
        }

        proxy_pass http://skillbridge_backend/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        # CORS headers - only ONE origin value
        add_header Access-Control-Allow-Origin $cors_origin always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Accept, Origin" always;
        add_header Access-Control-Allow-Credentials "true" always;
        
        access_log off;
    }

    # Auth endpoints
    location /auth/ {
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin $cors_origin always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Accept, Origin" always;
            add_header Access-Control-Allow-Credentials "true" always;
            add_header Access-Control-Max-Age 86400 always;
            add_header Content-Length 0;
            add_header Content-Type "text/plain charset=UTF-8";
            return 204;
        }

        proxy_pass http://skillbridge_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        # CORS headers - only ONE origin value
        add_header Access-Control-Allow-Origin $cors_origin always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Accept, Origin" always;
        add_header Access-Control-Allow-Credentials "true" always;
    }

    # All other API endpoints
    location / {
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin $cors_origin always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Accept, Origin" always;
            add_header Access-Control-Allow-Credentials "true" always;
            add_header Access-Control-Max-Age 86400 always;
            add_header Content-Length 0;
            add_header Content-Type "text/plain charset=UTF-8";
            return 204;
        }

        proxy_pass http://skillbridge_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        # CORS headers - only ONE origin value
        add_header Access-Control-Allow-Origin $cors_origin always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Accept, Origin" always;
        add_header Access-Control-Allow-Credentials "true" always;
    }

    # Logging
    access_log /var/log/nginx/skillbridge-access.log;
    error_log /var/log/nginx/skillbridge-error.log;
}
EOF

print_success "Configuration created with correct CORS handling"

# Enable the configuration
echo "🔗 Enabling configuration..."
sudo ln -sf /etc/nginx/sites-available/skillbridge /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/skillbridge-server.asolvitra.tech
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

# Wait for reload
sleep 3

# Test CORS from different origins
echo ""
echo "🧪 Testing CORS from different origins..."
echo ""

# Test 1: From skillbridge.asolvitra.tech
echo "1. Testing from https://skillbridge.asolvitra.tech"
CORS_RESPONSE=$(curl -s -H "Origin: https://skillbridge.asolvitra.tech" -I https://$DOMAIN/health 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
if echo "$CORS_RESPONSE" | grep -q "https://skillbridge.asolvitra.tech"; then
    print_success "CORS working for skillbridge.asolvitra.tech"
    print_info "$CORS_RESPONSE"
else
    print_warning "CORS not working for skillbridge.asolvitra.tech"
fi

echo ""

# Test 2: From www.skillbridge.asolvitra.tech
echo "2. Testing from https://www.skillbridge.asolvitra.tech"
CORS_RESPONSE=$(curl -s -H "Origin: https://www.skillbridge.asolvitra.tech" -I https://$DOMAIN/health 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
if echo "$CORS_RESPONSE" | grep -q "https://www.skillbridge.asolvitra.tech"; then
    print_success "CORS working for www.skillbridge.asolvitra.tech"
    print_info "$CORS_RESPONSE"
else
    print_warning "CORS not working for www.skillbridge.asolvitra.tech"
fi

echo ""

# Test 3: From skillbridge.vercel.app
echo "3. Testing from https://skillbridge.vercel.app"
CORS_RESPONSE=$(curl -s -H "Origin: https://skillbridge.vercel.app" -I https://$DOMAIN/health 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
if echo "$CORS_RESPONSE" | grep -q "https://skillbridge.vercel.app"; then
    print_success "CORS working for skillbridge.vercel.app"
    print_info "$CORS_RESPONSE"
else
    print_warning "CORS not working for skillbridge.vercel.app"
fi

echo ""

# Test 4: From unauthorized origin (should not have CORS)
echo "4. Testing from unauthorized origin (should be empty)"
CORS_RESPONSE=$(curl -s -H "Origin: https://evil.com" -I https://$DOMAIN/health 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
if [ -z "$CORS_RESPONSE" ]; then
    print_success "CORS correctly blocked for unauthorized origin"
else
    print_warning "CORS header present for unauthorized origin: $CORS_RESPONSE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ CORS Headers Fixed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔒 CORS Configuration:"
echo "   ✅ Only ONE origin value per request"
echo "   ✅ Dynamic origin matching"
echo "   ✅ Allowed origins:"
echo "      • https://skillbridge.asolvitra.tech"
echo "      • https://www.skillbridge.asolvitra.tech"
echo "      • https://skillbridge.vercel.app"
echo "      • http://localhost:* (for development)"
echo ""
echo "🚀 Your backend is now properly configured!"
echo ""
echo "📋 Test from your frontend:"
echo "   The CORS headers will now work correctly"
echo "   Each request will get the matching origin value"
echo ""