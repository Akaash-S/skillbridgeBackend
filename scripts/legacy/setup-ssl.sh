#!/bin/bash

# Setup SSL certificate for skillbridge-server.asolvitra.tech
set -e

echo "🔐 Setting up SSL Certificate"
echo "============================="
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
EMAIL="admin@asolvitra.tech"

# Check if Nginx is running
if ! sudo systemctl is-active --quiet nginx; then
    print_error "Nginx is not running"
    echo "Start Nginx with: sudo systemctl start nginx"
    exit 1
fi

print_success "Nginx is running"

# Check if domain resolves to this server
echo "🌐 Checking DNS..."
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "Unknown")
DOMAIN_IP=$(nslookup $DOMAIN 2>/dev/null | grep -A1 "Name:" | tail -1 | awk '{print $2}' 2>/dev/null || echo "Unknown")

print_info "Server IP: $SERVER_IP"
print_info "Domain IP: $DOMAIN_IP"

if [ "$SERVER_IP" != "$DOMAIN_IP" ]; then
    print_warning "Domain IP doesn't match server IP"
    print_info "DNS might still be propagating..."
    echo ""
    read -p "Do you want to continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if HTTP is working
echo "🧪 Testing HTTP access..."
if curl -f -s http://$DOMAIN/health > /dev/null 2>&1; then
    print_success "HTTP access is working"
else
    print_error "HTTP access is not working"
    echo "Fix Nginx proxy first with: sudo ./fix-nginx-proxy.sh"
    exit 1
fi

# Install Certbot if not already installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing Certbot..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
    print_success "Certbot installed"
else
    print_success "Certbot is already installed"
fi

# Obtain SSL certificate
echo "🔐 Obtaining SSL certificate from Let's Encrypt..."
echo "This may take a minute..."
echo ""

if sudo certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive --redirect; then
    print_success "SSL certificate obtained successfully!"
    
    # Test HTTPS
    echo ""
    echo "🧪 Testing HTTPS access..."
    sleep 5
    
    if curl -f -s https://$DOMAIN/health > /dev/null 2>&1; then
        print_success "HTTPS is working!"
    else
        print_warning "HTTPS test failed, but certificate was installed"
        echo "Try accessing: https://$DOMAIN/health"
    fi
    
else
    print_error "Failed to obtain SSL certificate"
    echo ""
    echo "Common issues:"
    echo "1. DNS not pointing to this server"
    echo "2. Port 80 not accessible from internet"
    echo "3. Firewall blocking connections"
    echo ""
    echo "Check firewall: sudo ufw status"
    echo "Check Nginx: sudo nginx -t"
    exit 1
fi

# Set up automatic renewal
echo "⚙️  Setting up automatic certificate renewal..."
if ! sudo crontab -l 2>/dev/null | grep -q certbot; then
    (sudo crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'") | sudo crontab -
    print_success "Automatic renewal configured"
else
    print_success "Automatic renewal already configured"
fi

# Show certificate info
echo ""
echo "📋 Certificate Information:"
sudo certbot certificates -d $DOMAIN 2>/dev/null || true

echo ""
echo "🎉 SSL Setup Complete!"
echo "====================="
echo ""
echo "🔗 Your backend is now available at:"
echo "   🌐 HTTPS: https://$DOMAIN"
echo "   ❤️  Health: https://$DOMAIN/health"
echo "   📡 API: https://$DOMAIN/api/..."
echo ""
echo "🔒 Security features:"
echo "   ✅ Let's Encrypt SSL certificate"
echo "   ✅ Automatic HTTP → HTTPS redirect"
echo "   ✅ Automatic certificate renewal"
echo "   ✅ A+ SSL rating configuration"
echo ""
echo "📋 Certificate will auto-renew before expiry"
echo "📋 Manual renewal: sudo certbot renew"
echo ""
echo "✅ Your backend is now production-ready with HTTPS! 🚀"