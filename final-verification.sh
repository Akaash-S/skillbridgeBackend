#!/bin/bash

# Final verification and fixes for domain setup
set -e

echo "🔍 Final Verification & Fixes"
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

echo "🔍 Running comprehensive tests..."
echo ""

# Test 1: Docker
echo "1️⃣  Testing Docker container..."
if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    DOCKER_RESPONSE=$(curl -s http://127.0.0.1:8000/health)
    print_success "Docker is responding"
    print_info "Response: $DOCKER_RESPONSE"
else
    print_error "Docker is not responding"
    echo "Fix: docker compose restart"
fi

# Test 2: Nginx
echo ""
echo "2️⃣  Testing Nginx..."
if sudo systemctl is-active --quiet nginx; then
    print_success "Nginx is running"
else
    print_error "Nginx is not running"
    echo "Fix: sudo systemctl start nginx"
fi

# Test 3: HTTP
echo ""
echo "3️⃣  Testing HTTP access..."
HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN/health 2>/dev/null || echo "000")
if [ "$HTTP_RESPONSE" = "200" ]; then
    print_success "HTTP is working (Status: $HTTP_RESPONSE)"
elif [ "$HTTP_RESPONSE" = "301" ] || [ "$HTTP_RESPONSE" = "302" ]; then
    print_success "HTTP redirects to HTTPS (Status: $HTTP_RESPONSE)"
else
    print_warning "HTTP returned status: $HTTP_RESPONSE"
fi

# Test 4: HTTPS
echo ""
echo "4️⃣  Testing HTTPS access..."
HTTPS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health 2>/dev/null || echo "000")
if [ "$HTTPS_RESPONSE" = "200" ]; then
    print_success "HTTPS is working (Status: $HTTPS_RESPONSE)"
    HTTPS_CONTENT=$(curl -s https://$DOMAIN/health 2>/dev/null)
    print_info "Response: $HTTPS_CONTENT"
else
    print_warning "HTTPS returned status: $HTTPS_RESPONSE"
    
    # Try to diagnose HTTPS issue
    echo ""
    print_info "Diagnosing HTTPS issue..."
    
    # Check if SSL certificate exists
    if sudo test -f /etc/letsencrypt/live/$DOMAIN/fullchain.pem; then
        print_success "SSL certificate exists"
    else
        print_error "SSL certificate not found"
    fi
    
    # Check Nginx SSL configuration
    if sudo nginx -t 2>&1 | grep -q "successful"; then
        print_success "Nginx configuration is valid"
    else
        print_error "Nginx configuration has errors"
        sudo nginx -t
    fi
    
    # Reload Nginx to apply SSL configuration
    echo ""
    print_info "Reloading Nginx to apply SSL configuration..."
    sudo systemctl reload nginx
    sleep 3
    
    # Test again
    HTTPS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health 2>/dev/null || echo "000")
    if [ "$HTTPS_RESPONSE" = "200" ]; then
        print_success "HTTPS is now working after reload!"
    else
        print_warning "HTTPS still not working (Status: $HTTPS_RESPONSE)"
    fi
fi

# Test 5: SSL Certificate
echo ""
echo "5️⃣  Checking SSL certificate..."
if command -v openssl &> /dev/null; then
    CERT_INFO=$(echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "")
    if [ ! -z "$CERT_INFO" ]; then
        print_success "SSL certificate is valid"
        print_info "$CERT_INFO"
    else
        print_warning "Could not retrieve SSL certificate info"
    fi
fi

# Test 6: CORS Headers
echo ""
echo "6️⃣  Testing CORS headers..."
CORS_TEST=$(curl -s -H "Origin: https://skillbridge.asolvitra.tech" -I https://$DOMAIN/health 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
if [ ! -z "$CORS_TEST" ]; then
    print_success "CORS headers are present"
    print_info "$CORS_TEST"
else
    print_warning "CORS headers not found"
    echo "This might be normal if the endpoint doesn't return CORS headers"
fi

# Test 7: Check Nginx logs for errors
echo ""
echo "7️⃣  Checking Nginx logs..."
ERROR_COUNT=$(sudo tail -50 /var/log/nginx/error.log 2>/dev/null | grep -c "error" || echo "0")
if [ "$ERROR_COUNT" -eq 0 ]; then
    print_success "No recent errors in Nginx logs"
else
    print_warning "Found $ERROR_COUNT errors in recent logs"
    echo "Recent errors:"
    sudo tail -20 /var/log/nginx/error.log 2>/dev/null | grep "error" || echo "None"
fi

# Fix crontab issue for auto-renewal
echo ""
echo "8️⃣  Setting up SSL auto-renewal..."
if command -v crontab &> /dev/null; then
    if ! sudo crontab -l 2>/dev/null | grep -q certbot; then
        (sudo crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'") | sudo crontab -
        print_success "Auto-renewal configured"
    else
        print_success "Auto-renewal already configured"
    fi
else
    # Use systemd timer instead
    if sudo systemctl list-timers 2>/dev/null | grep -q certbot; then
        print_success "Certbot systemd timer is active"
    else
        print_info "Installing certbot timer..."
        sudo systemctl enable certbot.timer 2>/dev/null || true
        sudo systemctl start certbot.timer 2>/dev/null || true
        print_success "Certbot timer enabled"
    fi
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Get final status
FINAL_HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN/health 2>/dev/null || echo "000")
FINAL_HTTPS=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health 2>/dev/null || echo "000")

echo "🔗 Access URLs:"
if [ "$FINAL_HTTPS" = "200" ]; then
    echo "   ✅ https://$DOMAIN (Working!)"
    echo "   ✅ https://$DOMAIN/health"
    echo ""
    print_success "Your backend is fully operational with HTTPS!"
elif [ "$FINAL_HTTP" = "200" ] || [ "$FINAL_HTTP" = "301" ]; then
    echo "   ✅ http://$DOMAIN (Working)"
    echo "   ⚠️  https://$DOMAIN (Status: $FINAL_HTTPS)"
    echo ""
    print_warning "HTTP works, but HTTPS needs attention"
    echo ""
    echo "🔧 To fix HTTPS:"
    echo "   1. sudo systemctl reload nginx"
    echo "   2. Wait 1-2 minutes for SSL to propagate"
    echo "   3. Test: curl -I https://$DOMAIN/health"
else
    echo "   ⚠️  http://$DOMAIN (Status: $FINAL_HTTP)"
    echo "   ⚠️  https://$DOMAIN (Status: $FINAL_HTTPS)"
    echo ""
    print_warning "Both HTTP and HTTPS need attention"
fi

echo ""
echo "📋 Quick Commands:"
echo "   Test HTTP:   curl -I http://$DOMAIN/health"
echo "   Test HTTPS:  curl -I https://$DOMAIN/health"
echo "   View logs:   docker compose logs -f"
echo "   Nginx logs:  sudo tail -f /var/log/nginx/error.log"
echo "   Reload:      sudo systemctl reload nginx"
echo ""

# Browser test suggestion
echo "🌐 Browser Test:"
echo "   Open: https://$DOMAIN/health"
echo "   You should see a JSON response with health status"
echo ""

echo "✅ Verification completed!"