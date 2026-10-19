#!/bin/bash

# Apply final Nginx configuration with correct CORS - generates config on VM
set -e

echo "🔧 Applying Final Nginx Configuration"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo ./apply-final-config.sh"
    exit 1
fi

echo "📋 Creating configuration file..."

# Create the configuration directly
cat > /etc/nginx/sites-available/skillbridge << 'NGINX_CONFIG'
# SkillBridge Backend - Final Nginx Configuration with Correct CORS

# Map to dynamically set CORS origin (only ONE value allowed)
map $http_origin $cors_origin {
    default "";
    "https://skillbridge.asolvitra.tech" $http_origin;
    "https://www.skillbridge.asolvitra.tech" $http_origin;
    "https://skillbridge.vercel.app" $http_origin;
}

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
        # Handle OPTIONS preflight
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin $cors_origin always;
            add_header Access-Control-Allow-Credentials "true" always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
            add_header Access-Control-Max-Age 86400 always;
            add_header Content-Length 0;
            add_header Content-Type "text/plain";
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
        add_header Access-Control-Allow-Credentials "true" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
        
        access_log off;
    }

    # Auth endpoints
    location /auth/ {
        # Handle OPTIONS preflight
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin $cors_origin always;
            add_header Access-Control-Allow-Credentials "true" always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
            add_header Access-Control-Max-Age 86400 always;
            add_header Content-Length 0;
            add_header Content-Type "text/plain";
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
        add_header Access-Control-Allow-Credentials "true" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
    }

    # All other API endpoints
    location / {
        # Handle OPTIONS preflight
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin $cors_origin always;
            add_header Access-Control-Allow-Credentials "true" always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
            add_header Access-Control-Max-Age 86400 always;
            add_header Content-Length 0;
            add_header Content-Type "text/plain";
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
        add_header Access-Control-Allow-Credentials "true" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
    }

    # Logging
    access_log /var/log/nginx/skillbridge-access.log;
    error_log /var/log/nginx/skillbridge-error.log;
}
NGINX_CONFIG

echo "✅ Configuration file created"

# Enable the site
echo "🔗 Enabling site..."
ln -sf /etc/nginx/sites-available/skillbridge /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/skillbridge-server.asolvitra.tech

# Test configuration
echo "🧪 Testing Nginx configuration..."
if nginx -t; then
    echo "✅ Configuration is valid"
else
    echo "❌ Configuration has errors"
    nginx -t
    exit 1
fi

# Reload Nginx
echo "🔄 Reloading Nginx..."
systemctl reload nginx

echo ""
echo "✅ Configuration applied successfully!"
echo ""
echo "🧪 Testing CORS..."
sleep 2

# Test CORS from different origins
echo ""
echo "1. Testing from https://skillbridge.asolvitra.tech"
CORS=$(curl -s -H "Origin: https://skillbridge.asolvitra.tech" -I https://skillbridge-server.asolvitra.tech/health 2>/dev/null | grep -i "access-control-allow-origin" || echo "Not found")
echo "   $CORS"

echo ""
echo "2. Testing from https://www.skillbridge.asolvitra.tech"
CORS=$(curl -s -H "Origin: https://www.skillbridge.asolvitra.tech" -I https://skillbridge-server.asolvitra.tech/health 2>/dev/null | grep -i "access-control-allow-origin" || echo "Not found")
echo "   $CORS"

echo ""
echo "3. Testing from https://skillbridge.vercel.app"
CORS=$(curl -s -H "Origin: https://skillbridge.vercel.app" -I https://skillbridge-server.asolvitra.tech/health 2>/dev/null | grep -i "access-control-allow-origin" || echo "Not found")
echo "   $CORS"

echo ""
echo "4. Testing from unauthorized origin (should be empty)"
CORS=$(curl -s -H "Origin: https://evil.com" -I https://skillbridge-server.asolvitra.tech/health 2>/dev/null | grep -i "access-control-allow-origin" || echo "✅ Correctly blocked")
echo "   $CORS"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Your backend is now fully configured!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔗 Access URLs:"
echo "   https://skillbridge-server.asolvitra.tech"
echo "   https://skillbridge-server.asolvitra.tech/health"
echo ""
echo "✅ CORS properly configured for:"
echo "   • https://skillbridge.asolvitra.tech"
echo "   • https://www.skillbridge.asolvitra.tech"
echo "   • https://skillbridge.vercel.app"
echo ""
echo "🚀 Your backend is production-ready!"
