#!/bin/bash

# Complete domain setup - All steps in one script
set -e

echo "🚀 Complete Domain Setup for SkillBridge"
echo "========================================"
echo ""
echo "Domain: skillbridge-server.asolvitra.tech"
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

print_step() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run with sudo"
    echo "Usage: sudo ./complete-domain-setup.sh"
    exit 1
fi

# Step 1: Update CORS
print_step "Step 1: Updating CORS Configuration"
if [ -f "update-cors.sh" ]; then
    chmod +x update-cors.sh
    sudo -u $SUDO_USER ./update-cors.sh <<< "y"
    print_success "CORS updated"
else
    print_warning "update-cors.sh not found, skipping"
fi

# Step 2: Fix port conflicts
print_step "Step 2: Fixing Port Conflicts"
if [ -f "fix-port-conflict.sh" ]; then
    chmod +x fix-port-conflict.sh
    ./fix-port-conflict.sh
    print_success "Port conflicts resolved"
else
    print_warning "fix-port-conflict.sh not found, skipping"
fi

# Step 3: Install Nginx
print_step "Step 3: Installing Nginx"
if ! command -v nginx &> /dev/null; then
    apt update
    apt install -y nginx
    print_success "Nginx installed"
else
    print_success "Nginx already installed"
fi

# Step 4: Configure firewall
print_step "Step 4: Configuring Firewall"
ufw allow 'Nginx Full' 2>/dev/null || true
ufw allow OpenSSH 2>/dev/null || true
ufw --force enable 2>/dev/null || true
print_success "Firewall configured"

# Step 5: Fix Nginx proxy configuration
print_step "Step 5: Configuring Nginx Proxy"
if [ -f "fix-nginx-proxy.sh" ]; then
    chmod +x fix-nginx-proxy.sh
    ./fix-nginx-proxy.sh
    print_success "Nginx proxy configured"
else
    print_error "fix-nginx-proxy.sh not found"
    exit 1
fi

# Step 6: Test HTTP access
print_step "Step 6: Testing HTTP Access"
sleep 5

DOMAIN="skillbridge-server.asolvitra.tech"
if curl -f -s http://$DOMAIN/health > /dev/null 2>&1; then
    print_success "HTTP access is working!"
    RESPONSE=$(curl -s http://$DOMAIN/health)
    print_info "Response: $RESPONSE"
else
    print_warning "HTTP access test failed"
    echo "You can still continue to set up SSL"
fi

# Step 7: Set up SSL
print_step "Step 7: Setting up SSL Certificate"
echo "This will obtain a Let's Encrypt SSL certificate..."
echo ""

read -p "Do you want to set up SSL now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "setup-ssl.sh" ]; then
        chmod +x setup-ssl.sh
        ./setup-ssl.sh
        print_success "SSL configured"
    else
        print_error "setup-ssl.sh not found"
        echo "You can set up SSL manually with:"
        echo "sudo certbot --nginx -d $DOMAIN --email admin@asolvitra.tech --agree-tos"
    fi
else
    print_info "Skipping SSL setup"
    echo "You can set up SSL later with: sudo ./setup-ssl.sh"
fi

# Final verification
print_step "Final Verification"
echo "Running verification tests..."
echo ""

if [ -f "verify-domain.sh" ]; then
    chmod +x verify-domain.sh
    sudo -u $SUDO_USER ./verify-domain.sh
else
    print_warning "verify-domain.sh not found, skipping verification"
fi

# Summary
print_step "🎉 Setup Complete!"
echo ""
echo "📊 Summary:"
echo "   🐳 Docker: Running on localhost:8000"
echo "   🌐 Nginx: Running on port 80/443"
echo "   🔗 Domain: $DOMAIN"
echo ""

# Check if HTTPS is working
if curl -f -s https://$DOMAIN/health > /dev/null 2>&1; then
    echo "🔗 Your backend is available at:"
    echo "   ✅ https://$DOMAIN"
    echo "   ✅ https://$DOMAIN/health"
    echo ""
    print_success "Your backend is fully configured with HTTPS!"
else
    echo "🔗 Your backend is available at:"
    echo "   ✅ http://$DOMAIN"
    echo "   ⚠️  https://$DOMAIN (SSL not set up yet)"
    echo ""
    print_info "To set up SSL, run: sudo ./setup-ssl.sh"
fi

echo ""
echo "📋 Management commands:"
echo "   Docker logs:  docker compose logs -f"
echo "   Nginx status: sudo systemctl status nginx"
echo "   SSL info:     sudo certbot certificates"
echo ""
echo "🚀 Your SkillBridge backend is ready for production!"