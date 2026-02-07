#!/bin/bash

# Deploy httpOnly cookie authentication
# This script updates both backend and Nginx to support secure cookie-based auth

set -e

echo "🔐 Deploying httpOnly Cookie Authentication"
echo "============================================"
echo ""

# Check if we're in the backend directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found"
    echo "Please run this script from the backend directory"
    exit 1
fi

echo "📋 Changes being deployed:"
echo "  ✓ Login endpoint sets httpOnly cookie"
echo "  ✓ MFA login endpoint sets httpOnly cookie"
echo "  ✓ New logout endpoint clears cookie"
echo "  ✓ Auth middleware reads token from cookie"
echo "  ✓ Nginx configured to allow credentials"
echo "  ✓ Flask CORS disabled (Nginx handles it)"
echo ""

# Step 1: Rebuild Docker container
echo "🐳 Step 1: Rebuilding Docker container..."
docker compose down
docker compose build --no-cache
docker compose up -d

echo "⏳ Waiting for container to start..."
sleep 15

# Test the application
echo "🧪 Testing backend..."
if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running"
else
    echo "❌ Backend failed to start"
    echo "Check logs: docker compose logs -f"
    exit 1
fi

# Step 2: Update Nginx configuration
echo ""
echo "🔧 Step 2: Updating Nginx configuration..."

# Backup current configuration
sudo cp /etc/nginx/sites-available/skillbridge /etc/nginx/sites-available/skillbridge.backup.$(date +%Y%m%d_%H%M%S)

# Create updated Nginx configuration with cookie support
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

# Step 3: Verify deployment
echo ""
echo "🧪 Step 3: Verifying deployment..."

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

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ httpOnly Cookie Authentication Deployed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔐 Security improvements:"
echo "   ✓ Tokens stored in httpOnly cookies (not accessible to JavaScript)"
echo "   ✓ Cookies only sent over HTTPS in production"
echo "   ✓ SameSite=Lax for CSRF protection"
echo "   ✓ 7-day cookie expiration"
echo "   ✓ Secure logout endpoint to clear cookies"
echo ""
echo "📝 API Changes:"
echo "   • POST /auth/login - Sets sb_session cookie"
echo "   • POST /auth/login/mfa - Sets sb_session cookie (requires idToken)"
echo "   • POST /auth/logout - Clears sb_session cookie"
echo "   • All protected endpoints read token from cookie"
echo ""
echo "⚠️  Frontend Update Required:"
echo "   1. Update auth service to use cookies instead of localStorage"
echo "   2. Add credentials: 'include' to all API requests"
echo "   3. Remove token from Authorization header"
echo "   4. Apply frontend security fixes: ./apply-security-fixes.sh"
echo ""
echo "🧪 Test the deployment:"
echo "   curl -c cookies.txt -X POST https://skillbridge-server.asolvitra.tech/auth/login \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"idToken\":\"your_firebase_token\"}'"
echo ""
echo "   curl -b cookies.txt https://skillbridge-server.asolvitra.tech/auth/me"
echo ""
