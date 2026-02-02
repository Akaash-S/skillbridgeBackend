#!/bin/bash

# Let's Encrypt SSL Setup for GCP Compute Engine
# Single container deployment

set -e

# Configuration
DOMAIN="${DOMAIN:-skillbridge-server.asolvitra.tech}"
EMAIL="${SSL_EMAIL:-admin@asolvitra.tech}"
SSL_DIR="./nginx/ssl"

echo "🔐 Setting up Let's Encrypt SSL for $DOMAIN..."

# Check if domain is provided
if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "localhost" ]; then
    echo "❌ Please set a valid DOMAIN in your .env file"
    echo "   Example: DOMAIN=your-domain.com"
    exit 1
fi

# Check if email is provided
if [ -z "$EMAIL" ]; then
    echo "❌ Please set SSL_EMAIL in your .env file"
    echo "   Example: SSL_EMAIL=admin@yourdomain.com"
    exit 1
fi

# Install certbot if not present
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y certbot
    elif command -v yum &> /dev/null; then
        sudo yum install -y certbot
    else
        echo "❌ Unable to install certbot automatically"
        echo "   Please install certbot manually and run this script again"
        exit 1
    fi
fi

# Create webroot directory
sudo mkdir -p /var/www/html/.well-known/acme-challenge
sudo chown -R www-data:www-data /var/www/html

# Stop the application temporarily
echo "🛑 Temporarily stopping application..."
docker-compose down

# Generate certificates using standalone mode
echo "📜 Generating Let's Encrypt certificates..."
sudo certbot certonly \
    --standalone \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --domains "$DOMAIN" \
    --non-interactive

# Copy certificates to our SSL directory
echo "📋 Copying certificates..."
sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/"
sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/"
sudo cp "/etc/letsencrypt/live/$DOMAIN/chain.pem" "$SSL_DIR/"

# Set proper permissions
sudo chown $(whoami):$(whoami) "$SSL_DIR"/*.pem
chmod 600 "$SSL_DIR"/*.pem

echo "✅ Let's Encrypt certificates installed!"

# Start the application
echo "🚀 Starting application with SSL certificates..."
docker-compose up -d

# Wait for service to be ready
echo "⏳ Waiting for service to start..."
sleep 10

# Test SSL
echo "🔍 Testing SSL configuration..."
if curl -f -s https://$DOMAIN/health > /dev/null 2>&1; then
    echo "✅ SSL is working correctly!"
else
    echo "⚠️  SSL test failed. Check the logs:"
    docker-compose logs --tail=20
fi

# Setup automatic renewal
echo "🔄 Setting up automatic certificate renewal..."

# Create renewal script
cat > /tmp/renew-ssl.sh << EOF
#!/bin/bash
# Auto-renewal script for Let's Encrypt certificates

set -e

DOMAIN="$DOMAIN"
SSL_DIR="$SSL_DIR"
COMPOSE_FILE="$(pwd)/docker-compose.yml"

echo "\$(date): Starting certificate renewal for \$DOMAIN"

# Stop application
cd $(pwd)
docker-compose down

# Renew certificates
certbot renew --standalone --quiet

# Copy new certificates
cp "/etc/letsencrypt/live/\$DOMAIN/fullchain.pem" "\$SSL_DIR/"
cp "/etc/letsencrypt/live/\$DOMAIN/privkey.pem" "\$SSL_DIR/"
cp "/etc/letsencrypt/live/\$DOMAIN/chain.pem" "\$SSL_DIR/"

# Set permissions
chown $(whoami):$(whoami) "\$SSL_DIR"/*.pem
chmod 600 "\$SSL_DIR"/*.pem

# Restart application
docker-compose up -d

echo "\$(date): Certificate renewal completed"
EOF

# Make script executable and move to system location
chmod +x /tmp/renew-ssl.sh
sudo mv /tmp/renew-ssl.sh /usr/local/bin/renew-skillbridge-ssl.sh

# Add cron job for automatic renewal (runs at 2 AM daily)
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/renew-skillbridge-ssl.sh >> /var/log/ssl-renewal.log 2>&1") | crontab -

echo "✅ Automatic renewal configured!"
echo ""
echo "🎉 SSL setup completed successfully!"
echo ""
echo "🔗 Your application is now available at:"
echo "   HTTPS: https://$DOMAIN"
echo "   HTTP:  http://$DOMAIN (redirects to HTTPS)"
echo ""
echo "📋 SSL Information:"
echo "   Domain: $DOMAIN"
echo "   Email: $EMAIL"
echo "   Certificates: $SSL_DIR"
echo "   Auto-renewal: Daily at 2 AM"
echo ""
echo "🔍 Test your SSL rating at:"
echo "   https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo ""
echo "📝 Manual renewal command:"
echo "   sudo /usr/local/bin/renew-skillbridge-ssl.sh"