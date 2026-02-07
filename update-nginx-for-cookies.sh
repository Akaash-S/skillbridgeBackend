#!/bin/bash

# Update Nginx configuration to support httpOnly cookies
# This script updates the CORS headers to allow credentials

echo "🔧 Updating Nginx configuration for httpOnly cookie support..."

# Backup current configuration
sudo cp /etc/nginx/sites-available/skillbridge /etc/nginx/sites-available/skillbridge.backup.$(date +%Y%m%d_%H%M%S)

# Create updated Nginx configuration
sudo tee /etc/nginx/sites-available/skillbridge > /dev/null <<'EOF'
# Map to determine allowed origin dynamically
map $http_origin $cors_origin {
    default "";
    "~^https://skillbridge\.asolvitra\.tech$" $http_origin;
    "~^https://www\.skillbridge\.asolvitra\.tech$" $http_origin;
    "~^https://skillbridge\.vercel\.app$" $http_origin;
}

# Upstream to Docker container
upstream skillbridge_backend {
    server localhost:8000;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name skillbridge-server.asolvitra.tech;
    
    # Allow Let's Encrypt challenges
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirect all other HTTP traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name skillbridge-server.asolvitra.tech;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/skillbridge-server.asolvitra.tech/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/skillbridge-server.asolvitra.tech/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Logging
    access_log /var/log/nginx/skillbridge-access.log;
    error_log /var/log/nginx/skillbridge-error.log;
    
    # Proxy settings
    location / {
        # Preflight requests
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' $cors_origin always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization, X-Requested-With, Accept, Origin' always;
            add_header 'Access-Control-Allow-Credentials' 'true' always;
            add_header 'Access-Control-Max-Age' 86400 always;
            add_header 'Content-Length' 0;
            add_header 'Content-Type' 'text/plain charset=UTF-8';
            return 204;
        }
        
        # Proxy to backend
        proxy_pass http://skillbridge_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # CORS headers for actual requests
        add_header 'Access-Control-Allow-Origin' $cors_origin always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization, X-Requested-With, Accept, Origin' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

echo "✅ Nginx configuration updated"

# Test configuration
echo "🧪 Testing Nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Configuration test passed"
    echo "🔄 Reloading Nginx..."
    sudo systemctl reload nginx
    echo "✅ Nginx reloaded successfully"
    echo ""
    echo "🎉 Nginx is now configured to support httpOnly cookies!"
    echo "   - Credentials are allowed in CORS"
    echo "   - Cookies will be sent with cross-origin requests"
else
    echo "❌ Configuration test failed"
    echo "🔙 Restoring backup..."
    sudo cp /etc/nginx/sites-available/skillbridge.backup.$(date +%Y%m%d)* /etc/nginx/sites-available/skillbridge
    exit 1
fi
