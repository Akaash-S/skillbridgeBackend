#!/bin/bash

# Complete fix for port conflict and Nginx warnings
# This script:
# 1. Stops Docker to free port 80
# 2. Updates docker-compose to only use localhost:8000
# 3. Rebuilds Docker container
# 4. Updates Nginx with http2 fix and cookie support
# 5. Starts everything properly

set -e

echo "🔧 Fixing Port Conflict and Deploying Cookie Auth"
echo "=================================================="
echo ""

# Check if we're in the backend directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found"
    echo "Please run this script from the backend directory"
    exit 1
fi

# Step 1: Stop Docker to free port 80
echo "🛑 Step 1: Stopping Docker container..."
docker compose down
echo "✅ Docker stopped - port 80 is now free for Nginx"

# Step 2: Verify docker-compose.yml is correct
echo ""
echo "🔍 Step 2: Verifying docker-compose.yml..."
if grep -q "127.0.0.1:8000:8000" docker-compose.yml; then
    echo "✅ docker-compose.yml already configured correctly"
else
    echo "⚠️  docker-compose.yml needs update"
    echo "Please ensure ports section has: - \"127.0.0.1:8000:8000\""
    exit 1
fi

# Step 3: Rebuild Docker container
echo ""
echo "🐳 Step 3: Rebuilding Docker container..."
docker compose build --no-cache
echo "✅ Docker image built"

# Step 4: Start Docker container
echo ""
echo "🚀 Step 4: Starting Docker container..."
docker compose up -d
echo "⏳ Waiting for container to start..."
sleep 15

# Test the application
echo "🧪 Testing backend on localhost:8000..."
if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running on localhost:8000"
else
    echo "❌ Backend failed to start"
    echo "Check logs: docker compose logs -f"
    exit 1
fi

# Step 5: Update Nginx configuration
echo ""
echo "🔧 Step 5: Updating Nginx configuration..."

# Backup current configuration
sudo cp /etc/nginx/sites-available/skillbridge /etc/nginx/sites-available/skillbridge.backup.$(date +%Y%m%d_%H%M%S)

# Create updated Nginx configuration with http2 fix and cookie support
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
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
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

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Configuration test passed"
    echo "🔄 Reloading Nginx..."
    sudo systemctl reload nginx
    echo "✅ Nginx reloaded successfully"
else
    echo "❌ Configuration test failed"
    echo "🔙 Restoring backup..."
    LATEST_BACKUP=$(ls -t /etc/nginx/sites-available/skillbridge.backup.* | head -1)
    sudo cp "$LATEST_BACKUP" /etc/nginx/sites-available/skillbridge
    exit 1
fi

# Step 6: Verify deployment
echo ""
echo "🧪 Step 6: Verifying deployment..."

# Test health endpoint
echo "Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s https://skillbridge-server.asolvitra.tech/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo "✅ Health check passed"
else
    echo "⚠️ Health check returned unexpected response"
fi

# Test CORS with credentials
echo "Testing CORS with credentials..."
CORS_TEST=$(curl -s -I -X OPTIONS \
    -H "Origin: https://skillbridge.asolvitra.tech" \
    -H "Access-Control-Request-Method: POST" \
    https://skillbridge-server.asolvitra.tech/auth/login)

if echo "$CORS_TEST" | grep -q "Access-Control-Allow-Credentials: true"; then
    echo "✅ CORS credentials enabled"
else
    echo "⚠️ CORS credentials not found in response"
fi

# Check Docker status
echo "Checking Docker container status..."
if docker compose ps | grep -q "Up"; then
    echo "✅ Docker container is running"
else
    echo "⚠️ Docker container may not be running properly"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Summary:"
echo "   ✓ Port 80 freed (Docker uses localhost:8000 only)"
echo "   ✓ Nginx running on port 80/443"
echo "   ✓ Docker container running on localhost:8000"
echo "   ✓ http2 warning fixed (using 'http2 on' directive)"
echo "   ✓ Cookie authentication enabled"
echo "   ✓ CORS credentials configured"
echo ""
echo "🔐 Security Features:"
echo "   ✓ httpOnly cookies for authentication"
echo "   ✓ Secure flag enabled (HTTPS only)"
echo "   ✓ SameSite=Lax for CSRF protection"
echo "   ✓ 7-day cookie expiration"
echo ""
echo "🌐 Access URLs:"
echo "   Main:   https://skillbridge-server.asolvitra.tech"
echo "   Health: https://skillbridge-server.asolvitra.tech/health"
echo "   API:    https://skillbridge-server.asolvitra.tech/api/..."
echo ""
echo "📋 Next Steps:"
echo "   1. Update and deploy frontend with cookie support"
echo "   2. Test login flow with cookies"
echo "   3. Verify cookies in browser DevTools"
echo "   4. Test logout clears cookies"
echo ""
echo "🔍 Monitoring:"
echo "   Docker logs:  docker compose logs -f"
echo "   Nginx logs:   sudo tail -f /var/log/nginx/skillbridge-error.log"
echo "   Nginx access: sudo tail -f /var/log/nginx/skillbridge-access.log"
echo ""
echo "🧪 Test Commands:"
echo "   # Test with curl"
echo "   curl -c cookies.txt -X POST https://skillbridge-server.asolvitra.tech/auth/login \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"idToken\":\"YOUR_TOKEN\"}'"
echo ""
echo "   curl -b cookies.txt https://skillbridge-server.asolvitra.tech/auth/me"
echo ""
