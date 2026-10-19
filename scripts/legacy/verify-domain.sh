#!/bin/bash

# Domain verification script for skillbridge-server.asolvitra.tech
set -e

echo "🔍 Verifying Domain Setup"
echo "========================="
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

echo "🌐 Testing domain: $DOMAIN"
echo ""

# Test 1: DNS Resolution
echo "1. DNS Resolution Test"
if nslookup $DOMAIN > /dev/null 2>&1; then
    IP=$(nslookup $DOMAIN | grep -A1 "Name:" | tail -1 | awk '{print $2}' 2>/dev/null || echo "Unknown")
    print_success "DNS resolves to: $IP"
else
    print_error "DNS resolution failed"
    echo "   Make sure your domain points to this server"
fi

# Test 2: Local Docker Container
echo ""
echo "2. Local Docker Container Test"
if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    print_success "Docker container responding on localhost:8000"
else
    print_error "Docker container not responding"
    echo "   Run: docker compose ps"
    echo "   Check: docker compose logs -f"
fi

# Test 3: Nginx Status
echo ""
echo "3. Nginx Status Test"
if systemctl is-active --quiet nginx; then
    print_success "Nginx is running"
    
    # Check if our site is enabled
    if [ -f "/etc/nginx/sites-enabled/skillbridge" ]; then
        print_success "SkillBridge site is enabled"
    else
        print_warning "SkillBridge site not enabled"
    fi
else
    print_error "Nginx is not running"
    echo "   Run: sudo systemctl start nginx"
fi

# Test 4: HTTP Access
echo ""
echo "4. HTTP Access Test"
if curl -f -s -o /dev/null -w "%{http_code}" http://$DOMAIN/health 2>/dev/null | grep -q "200"; then
    print_success "HTTP access working"
else
    print_warning "HTTP access failed"
    echo "   This might be normal if HTTPS redirect is active"
fi

# Test 5: HTTPS Access
echo ""
echo "5. HTTPS Access Test"
if curl -f -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health 2>/dev/null | grep -q "200"; then
    print_success "HTTPS access working"
    
    # Check certificate details
    CERT_EXPIRY=$(echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    if [ ! -z "$CERT_EXPIRY" ]; then
        print_info "SSL certificate expires: $CERT_EXPIRY"
    fi
else
    print_warning "HTTPS access failed"
    echo "   SSL certificate might not be set up yet"
    echo "   Run: sudo certbot --nginx -d $DOMAIN"
fi

# Test 6: CORS Headers
echo ""
echo "6. CORS Headers Test"
CORS_HEADER=$(curl -s -H "Origin: https://skillbridge.asolvitra.tech" -I https://$DOMAIN/health 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
if [ ! -z "$CORS_HEADER" ]; then
    print_success "CORS headers present"
    print_info "CORS: $CORS_HEADER"
else
    print_warning "CORS headers not found"
fi

# Test 7: API Endpoint Test
echo ""
echo "7. API Endpoint Test"
API_RESPONSE=$(curl -s https://$DOMAIN/health 2>/dev/null || curl -s http://$DOMAIN/health 2>/dev/null || echo "")
if echo "$API_RESPONSE" | grep -q "status\|health\|ok" 2>/dev/null; then
    print_success "API endpoint responding correctly"
    print_info "Response: $API_RESPONSE"
else
    print_warning "API endpoint response unexpected"
    echo "   Response: $API_RESPONSE"
fi

# Test 8: Frontend Integration Test
echo ""
echo "8. Frontend Integration Test"
print_info "Testing from your frontend domains..."

# Test CORS from different origins
for origin in "https://skillbridge.asolvitra.tech" "https://www.skillbridge.asolvitra.tech" "https://skillbridge.vercel.app"; do
    CORS_TEST=$(curl -s -H "Origin: $origin" -I https://$DOMAIN/health 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
    if [ ! -z "$CORS_TEST" ]; then
        print_success "CORS working for: $origin"
    else
        print_warning "CORS may not work for: $origin"
    fi
done

echo ""
echo "📊 Summary"
echo "=========="

# Get current server IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "Unknown")
echo "Server IP: $SERVER_IP"

# Check if domain points to this server
DOMAIN_IP=$(nslookup $DOMAIN 2>/dev/null | grep -A1 "Name:" | tail -1 | awk '{print $2}' 2>/dev/null || echo "Unknown")
echo "Domain IP: $DOMAIN_IP"

if [ "$SERVER_IP" = "$DOMAIN_IP" ]; then
    print_success "Domain correctly points to this server"
else
    print_warning "Domain IP ($DOMAIN_IP) doesn't match server IP ($SERVER_IP)"
    echo "   Update your DNS records to point to: $SERVER_IP"
fi

echo ""
echo "🔗 Access URLs:"
echo "   🌐 Main:     https://$DOMAIN"
echo "   ❤️  Health:   https://$DOMAIN/health"
echo "   📡 API:      https://$DOMAIN/api/..."
echo ""

# Show next steps if issues found
echo "🔧 If you see any warnings above:"
echo "   1. DNS Issues: Update your domain's A record to point to $SERVER_IP"
echo "   2. SSL Issues: Run 'sudo certbot --nginx -d $DOMAIN'"
echo "   3. Docker Issues: Run 'docker compose logs -f'"
echo "   4. Nginx Issues: Run 'sudo nginx -t' and 'sudo systemctl reload nginx'"
echo ""

echo "✅ Domain verification completed!"