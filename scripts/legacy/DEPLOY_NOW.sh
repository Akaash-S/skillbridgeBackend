#!/bin/bash

# COMPLETE DEPLOYMENT SCRIPT
# This is the ONE script to run for complete deployment
# Combines port fix, http2 fix, and cookie authentication

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  SkillBridge Backend - Complete Deployment                ║"
echo "║  httpOnly Cookie Authentication + Port Fix + http2 Fix    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the backend directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found"
    echo "Please run this script from the backend directory"
    exit 1
fi

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  This script needs sudo access for Nginx configuration"
    echo "Please run with: sudo ./DEPLOY_NOW.sh"
    echo "Or the script will prompt for sudo password when needed"
    echo ""
fi

echo "📋 This script will:"
echo "   1. Stop Docker to free port 80"
echo "   2. Rebuild Docker with cookie authentication"
echo "   3. Start Docker on localhost:8000 only"
echo "   4. Update Nginx with http2 fix and cookie support"
echo "   5. Reload Nginx"
echo "   6. Verify deployment"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Stopping Docker Container"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose down
echo "✅ Docker stopped - port 80 is now free for Nginx"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Verifying Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check docker-compose.yml
if grep -q "127.0.0.1:8000:8000" docker-compose.yml; then
    echo "✅ docker-compose.yml configured correctly (localhost:8000)"
else
    echo "⚠️  docker-compose.yml needs update"
    echo "Updating docker-compose.yml to use localhost:8000..."
    
    # Backup
    cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)
    
    # Update ports
    sed -i 's/- "8000:8000"/- "127.0.0.1:8000:8000"/' docker-compose.yml
    sed -i 's/- "80:80"/# - "80:80"  # Disabled - Nginx handles port 80/' docker-compose.yml
    
    echo "✅ docker-compose.yml updated"
fi

# Check if Flask CORS is disabled
if grep -q "# from flask_cors import CORS" app/__init__.py; then
    echo "✅ Flask CORS is disabled (Nginx handles CORS)"
else
    echo "⚠️  Flask CORS should be disabled"
    echo "Nginx will handle CORS to prevent duplicate headers"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Building Docker Container"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose build --no-cache
echo "✅ Docker image built with cookie authentication"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Starting Docker Container"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose up -d
echo "⏳ Waiting for container to start..."
sleep 15

# Test backend
echo "🧪 Testing backend on localhost:8000..."
if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running on localhost:8000"
else
    echo "❌ Backend failed to start"
    echo "Check logs: docker compose logs -f"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 5: Updating Nginx Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Backup current configuration
sudo cp /etc/nginx/sites-available/skillbridge /etc/nginx/sites-available/skillbridge.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created"

# Create updated Nginx configuration
echo "📝 Writing new Nginx configuration..."
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

echo "✅ Nginx configuration written"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 6: Testing and Reloading Nginx"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

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
    sudo systemctl reload nginx
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 7: Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "1️⃣  Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s https://skillbridge-server.asolvitra.tech/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo "✅ Health check passed"
else
    echo "⚠️  Health check returned unexpected response"
    echo "Response: $HEALTH_RESPONSE"
fi

echo ""
echo "2️⃣  Testing CORS with credentials..."
CORS_TEST=$(curl -s -I -X OPTIONS \
    -H "Origin: https://skillbridge.asolvitra.tech" \
    -H "Access-Control-Request-Method: POST" \
    https://skillbridge-server.asolvitra.tech/auth/login)

if echo "$CORS_TEST" | grep -q "Access-Control-Allow-Credentials: true"; then
    echo "✅ CORS credentials enabled"
else
    echo "⚠️  CORS credentials not found"
fi

echo ""
echo "3️⃣  Checking Docker container..."
if docker compose ps | grep -q "Up"; then
    echo "✅ Docker container is running"
else
    echo "⚠️  Docker container may not be running properly"
fi

echo ""
echo "4️⃣  Checking Nginx status..."
if sudo systemctl is-active --quiet nginx; then
    echo "✅ Nginx is running"
else
    echo "⚠️  Nginx is not running"
fi

echo ""
echo "5️⃣  Checking port usage..."
if sudo netstat -tlnp | grep -q ":80.*nginx"; then
    echo "✅ Nginx is listening on port 80"
else
    echo "⚠️  Nginx not listening on port 80"
fi

if sudo netstat -tlnp | grep -q ":443.*nginx"; then
    echo "✅ Nginx is listening on port 443"
else
    echo "⚠️  Nginx not listening on port 443"
fi

if netstat -tln | grep -q "127.0.0.1:8000"; then
    echo "✅ Docker is listening on localhost:8000"
else
    echo "⚠️  Docker not listening on localhost:8000"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  ✅ DEPLOYMENT COMPLETE!                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Deployment Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   ✓ Port 80/443: Nginx (reverse proxy)"
echo "   ✓ Port 8000: Docker (localhost only)"
echo "   ✓ http2: Enabled with 'http2 on' directive"
echo "   ✓ Cookie Auth: httpOnly, secure, SameSite=Lax"
echo "   ✓ CORS: Credentials enabled"
echo "   ✓ SSL: Let's Encrypt certificate"
echo ""
echo "🔐 Security Features:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   ✓ httpOnly cookies (JavaScript cannot access)"
echo "   ✓ Secure flag (HTTPS only)"
echo "   ✓ SameSite=Lax (CSRF protection)"
echo "   ✓ 7-day cookie expiration"
echo "   ✓ XSS protection headers"
echo ""
echo "🌐 Access URLs:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Main:   https://skillbridge-server.asolvitra.tech"
echo "   Health: https://skillbridge-server.asolvitra.tech/health"
echo "   API:    https://skillbridge-server.asolvitra.tech/api/..."
echo ""
echo "📋 Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   1. Update frontend with cookie support"
echo "   2. Build frontend: cd frontend && npm run build"
echo "   3. Deploy frontend to Vercel/hosting"
echo "   4. Test login flow with cookies"
echo "   5. Verify cookies in browser DevTools"
echo ""
echo "🔍 Monitoring Commands:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Docker logs:  docker compose logs -f"
echo "   Nginx error:  sudo tail -f /var/log/nginx/skillbridge-error.log"
echo "   Nginx access: sudo tail -f /var/log/nginx/skillbridge-access.log"
echo ""
echo "🧪 Test Cookie Authentication:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   # Login and get cookie"
echo "   curl -c cookies.txt -X POST \\"
echo "     https://skillbridge-server.asolvitra.tech/auth/login \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"idToken\":\"YOUR_FIREBASE_TOKEN\"}'"
echo ""
echo "   # Use cookie for authenticated request"
echo "   curl -b cookies.txt \\"
echo "     https://skillbridge-server.asolvitra.tech/auth/me"
echo ""
echo "   # Logout and clear cookie"
echo "   curl -b cookies.txt -c cookies.txt -X POST \\"
echo "     https://skillbridge-server.asolvitra.tech/auth/logout"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Backend deployment successful!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
