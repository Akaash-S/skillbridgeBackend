#!/bin/bash

# Quick domain test script
echo "🧪 Quick Domain Test"
echo "==================="
echo ""

DOMAIN="skillbridge-server.asolvitra.tech"

echo "Testing $DOMAIN..."
echo ""

# Test HTTP
echo "1. HTTP Test:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN/health 2>/dev/null || echo "Failed")
echo "   Status: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
    echo "   ✅ HTTP Working"
else
    echo "   ❌ HTTP Failed"
fi

echo ""

# Test HTTPS
echo "2. HTTPS Test:"
HTTPS_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health 2>/dev/null || echo "Failed")
echo "   Status: $HTTPS_CODE"
if [ "$HTTPS_CODE" = "200" ]; then
    echo "   ✅ HTTPS Working"
    RESPONSE=$(curl -s https://$DOMAIN/health 2>/dev/null)
    echo "   Response: $RESPONSE"
else
    echo "   ⚠️  HTTPS Status: $HTTPS_CODE"
fi

echo ""

# Test from browser
echo "3. Browser Test:"
echo "   Open this URL in your browser:"
echo "   👉 https://$DOMAIN/health"
echo ""

# Show certificate info
echo "4. SSL Certificate:"
CERT_EXPIRY=$(echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2 || echo "Unable to retrieve")
echo "   Expires: $CERT_EXPIRY"
echo ""

if [ "$HTTPS_CODE" = "200" ]; then
    echo "🎉 Your domain is fully working with HTTPS!"
else
    echo "⚠️  HTTPS needs attention. Try:"
    echo "   sudo systemctl reload nginx"
    echo "   Then test again: ./test-domain.sh"
fi