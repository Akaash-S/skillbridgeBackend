#!/bin/bash

# Fix Nginx Configuration for SkillBridge Server

echo "🔧 Fixing Nginx Configuration"
echo "============================="

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

# Check if running with sudo privileges for nginx operations
if [ "$EUID" -ne 0 ]; then
    print_warning "This script needs sudo privileges for nginx configuration"
    echo "Run: sudo ./fix-nginx-config.sh"
    echo "Or run individual commands with sudo"
fi

# Step 1: Configure global rate limiting zones
print_status "Configuring global rate limiting zones..."
sudo mkdir -p /etc/nginx/conf.d

# Write global shared rate limiting configuration (in http context)
sudo tee /etc/nginx/conf.d/rate_limits.conf > /dev/null << 'EOF'
# SkillBridge Rate Limiting Zones (Shared globally in http block)
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;
EOF

# Clean up any duplicate definitions from main nginx.conf and sites-available
print_status "Cleaning up duplicate rate limiting zones from configuration files..."
if [ -f /etc/nginx/nginx.conf ]; then
    # Backup nginx.conf
    sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)
    sudo sed -i '/limit_req_zone/d' /etc/nginx/nginx.conf
fi

for f in /etc/nginx/sites-available/*; do
    if [ -f "$f" ]; then
        sudo sed -i '/limit_req_zone/d' "$f"
    fi
done

# Step 2: Remove existing site configuration if it exists
print_status "Removing existing site configuration..."
sudo rm -f /etc/nginx/sites-enabled/skillbridge-server.asolvitra.tech
sudo rm -f /etc/nginx/sites-available/skillbridge-server.asolvitra.tech

# Step 3: Copy the corrected site configuration
print_status "Installing corrected site configuration..."
sudo cp skillbridge-server-site.conf /etc/nginx/sites-available/skillbridge-server.asolvitra.tech

# Step 4: Enable the site
print_status "Enabling the site..."
sudo ln -sf /etc/nginx/sites-available/skillbridge-server.asolvitra.tech /etc/nginx/sites-enabled/

# Step 5: Remove default site if it exists
print_status "Removing default site..."
sudo rm -f /etc/nginx/sites-enabled/default

# Step 6: Test nginx configuration
print_status "Testing nginx configuration..."
if sudo nginx -t; then
    print_success "Nginx configuration is valid"
    
    # Step 7: Reload nginx
    print_status "Reloading nginx..."
    if sudo systemctl reload nginx; then
        print_success "Nginx reloaded successfully"
    else
        print_error "Failed to reload nginx"
        exit 1
    fi
else
    print_error "Nginx configuration test failed"
    echo ""
    echo "📋 Configuration files:"
    echo "   Main config: /etc/nginx/nginx.conf"
    echo "   Site config: /etc/nginx/sites-available/skillbridge-server.asolvitra.tech"
    echo ""
    echo "🔧 Manual fix:"
    echo "   sudo nginx -t  # See detailed error"
    echo "   sudo nano /etc/nginx/nginx.conf  # Edit main config"
    exit 1
fi

# Step 8: Check nginx status
print_status "Checking nginx status..."
if sudo systemctl is-active --quiet nginx; then
    print_success "Nginx is running"
else
    print_warning "Nginx is not running, starting it..."
    sudo systemctl start nginx
fi

echo ""
print_success "🎉 Nginx configuration fixed successfully!"
echo ""
echo "📊 Configuration Summary:"
echo "   Site: skillbridge-server.asolvitra.tech"
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