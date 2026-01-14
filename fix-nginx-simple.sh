#!/bin/bash

# Simple Nginx Fix - Create the missing site configuration

echo "🔧 Simple Nginx Configuration Fix"
echo "================================="

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

# Check if we're in the backend directory
if [ ! -f "skillbridge-server-site.conf" ]; then
    print_error "skillbridge-server-site.conf not found"
    echo "Please run this script from the backend directory"
    exit 1
fi

# Step 1: Create the sites-available directory if it doesn't exist
print_status "Creating nginx directories..."
sudo mkdir -p /etc/nginx/sites-available
sudo mkdir -p /etc/nginx/sites-enabled

# Step 2: Copy the site configuration
print_status "Installing site configuration..."
sudo cp skillbridge-server-site.conf /etc/nginx/sites-available/skillbridge-server.asolvitra.tech

# Step 3: Create the symbolic link
print_status "Creating symbolic link..."
sudo ln -sf /etc/nginx/sites-available/skillbridge-server.asolvitra.tech /etc/nginx/sites-enabled/skillbridge-server.asolvitra.tech

# Step 4: Remove default site if it exists
print_status "Removing default site..."
sudo rm -f /etc/nginx/sites-enabled/default

# Step 5: Check if main nginx.conf includes sites-enabled
print_status "Checking main nginx.conf..."
if ! grep -q "sites-enabled" /etc/nginx/nginx.conf; then
    print_status "Adding sites-enabled include to nginx.conf..."
    
    # Backup nginx.conf
    sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)
    
    # Add include directive to http block
    sudo sed -i '/http {/a\\n\t# Include site configurations\n\tinclude /etc/nginx/sites-enabled/*;\n' /etc/nginx/nginx.conf
fi

# Step 6: Add rate limiting zones if they don't exist
if ! grep -q "limit_req_zone.*zone=api" /etc/nginx/nginx.conf; then
    print_status "Adding rate limiting zones..."
    sudo sed -i '/http {/a\\n\t# Rate limiting zones\n\tlimit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;\n\tlimit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;\n' /etc/nginx/nginx.conf
fi

# Step 7: Test nginx configuration
print_status "Testing nginx configuration..."
if sudo nginx -t; then
    print_success "Nginx configuration is valid"
    
    # Reload nginx
    print_status "Reloading nginx..."
    sudo systemctl reload nginx
    print_success "Nginx reloaded successfully"
else
    print_error "Nginx configuration test failed"
    echo ""
    echo "📋 Let's check what's wrong:"
    sudo nginx -t 2>&1
    echo ""
    echo "🔧 Files created:"
    echo "   /etc/nginx/sites-available/skillbridge-server.asolvitra.tech"
    echo "   /etc/nginx/sites-enabled/skillbridge-server.asolvitra.tech"
    exit 1
fi

# Step 8: Verify files exist
print_status "Verifying configuration files..."
if [ -f "/etc/nginx/sites-enabled/skillbridge-server.asolvitra.tech" ]; then
    print_success "Site configuration file exists"
else
    print_error "Site configuration file missing"
fi

# Step 9: Check nginx status
if sudo systemctl is-active --quiet nginx; then
    print_success "Nginx is running"
else
    print_status "Starting nginx..."
    sudo systemctl start nginx
fi

echo ""
print_success "🎉 Nginx configuration completed!"
echo ""
echo "📊 Configuration Summary:"
echo "   Site config: /etc/nginx/sites-available/skillbridge-server.asolvitra.tech"
echo "   Enabled: /etc/nginx/sites-enabled/skillbridge-server.asolvitra.tech"
echo "   Backend: 127.0.0.1:8080"
echo ""
echo "🔧 Next Steps:"
echo "1. Test backend: curl http://localhost:8080/health"
echo "2. Generate SSL: sudo certbot --nginx -d skillbridge-server.asolvitra.tech"
echo "3. Test external: curl -I https://skillbridge-server.asolvitra.tech/health"
echo ""
echo "📋 Troubleshooting:"
echo "   Test config: sudo nginx -t"
echo "   Check files: ls -la /etc/nginx/sites-enabled/"
echo "   View logs: sudo tail -f /var/log/nginx/error.log"
echo ""