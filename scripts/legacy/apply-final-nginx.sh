#!/bin/bash

# Apply final Nginx configuration with correct CORS
set -e

echo "🔧 Applying Final Nginx Configuration"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo ./apply-final-nginx.sh"
    exit 1
fi

# Copy the configuration
echo "📋 Copying configuration..."
cp nginx-final-config.conf /etc/nginx/sites-available/skillbridge

# Enable the site
echo "🔗 Enabling site..."
ln -sf /etc/nginx/sites-available/skillbridge /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/skillbridge-server.asolvitra.tech

# Test configuration
echo "🧪 Testing Nginx configuration..."
if nginx -t; then
    echo "✅ Configuration is valid"
else
    echo "❌ Configuration has errors"
    exit 1
fi

# Reload Nginx
echo "🔄 Reloading Nginx..."
systemctl reload nginx

echo ""
echo "✅ Configuration applied successfully!"
echo ""
echo "🧪 Test CORS with:"
echo "curl -H 'Origin: https://skillbridge.asolvitra.tech' -I https://skillbridge-server.asolvitra.tech/health"
