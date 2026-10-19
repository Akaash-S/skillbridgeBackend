#!/bin/bash

# Replace Nginx Configuration with Standalone Version

echo "🔧 Installing Standalone Nginx Configuration"
echo "============================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if we have the standalone config file
if [ ! -f "nginx-standalone.conf" ]; then
    print_error "nginx-standalone.conf not found"
    echo "Please run this script from the backend directory"
    exit 1
fi

# Step 1: Backup existing nginx.conf
print_status "Backing up existing nginx configuration..."
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)
print_success "Backup created"

# Step 2: Replace nginx.conf with standalone version
print_status "Installing standalone nginx configuration..."
sudo cp nginx-standalone.conf /etc/nginx/nginx.conf
print_success "Standalone configuration installed"

# Step 3: Remove sites-enabled directory to avoid conflicts
print_status "Cleaning up sites-enabled directory..."
sudo rm -rf /etc/nginx/sites-enabled/*
print_success "Sites-enabled cleaned"

# Step 4: Test nginx configuration
print_status "Testing nginx configuration..."
if sudo nginx -t; then
    print_success "Nginx configuration is valid"
    
    # Step 5: Reload nginx
    print_status "Reloading nginx..."
    if sudo systemctl reload nginx; then
        print_success "Nginx reloaded successfully"
    else
        print_error "Failed to reload nginx"
        print_status "Trying to restart nginx..."
        sudo systemctl restart nginx
    fi
else
    print_error "Nginx configuration test failed"
    echo ""
    echo "📋 Detailed error:"
    sudo nginx -t 2>&1
    echo ""
    echo "🔧 Restoring backup..."
    sudo cp /etc/nginx/nginx.conf.backup.$(date +%Y%m%d)* /etc/nginx/nginx.conf
    sudo nginx -t
    exit 1
fi

# Step 6: Check nginx status
print_status "Checking nginx status..."
if sudo systemctl is-active --quiet nginx; then
    print_success "Nginx is running"
else
    print_warning "Nginx is not running, starting it..."
    sudo systemctl start nginx
fi

# Step 7: Test the configuration
print_status "Testing HTTP redirect..."
if curl -I http://skillbridge-server.asolvitra.tech 2>/dev/null | grep -q "301"; then
    print_success "HTTP to HTTPS redirect is working"
else
    print_warning "HTTP redirect test failed (this is normal if DNS isn't configured)"
fi

echo ""
print_success "🎉 Standalone Nginx configuration installed successfully!"
echo ""
echo "📊 Configuration Summary:"
echo "   Configuration: Standalone (single file)"
echo "   Server: skillbridge-server.asolvitra.tech"
echo "   Backend: 127.0.0.1:8080"
echo "   Rate limiting: Enabled"
echo "   CORS: Configured for https://skillbridge.asolvitra.tech"
echo ""
echo "🔧 Next Steps:"
echo "1. Ensure backend is running: curl http://localhost:8080/health"
echo "2. Generate SSL certificate: sudo certbot --nginx -d skillbridge-server.asolvitra.tech"
echo "3. Test external access: curl -I https://skillbridge-server.asolvitra.tech/health"
echo ""
echo "📋 Useful Commands:"
echo "   Test config: sudo nginx -t"
echo "   Reload: sudo systemctl reload nginx"
echo "   Status: sudo systemctl status nginx"
echo "   Logs: sudo tail -f /var/log/nginx/error.log"
echo ""
echo "🔄 If you need to restore the original config:"
echo "   sudo cp /etc/nginx/nginx.conf.backup.* /etc/nginx/nginx.conf"
echo "   sudo systemctl reload nginx"
echo ""