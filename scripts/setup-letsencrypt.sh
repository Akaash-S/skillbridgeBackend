#!/bin/bash

# Setup Let's Encrypt SSL certificates for production
# Run this script on your production server

set -e

DOMAIN="skillbridge-server.asolvitra.tech"
EMAIL="admin@asolvitra.tech"  # Change this to your email
SSL_DIR="./nginx/ssl"

echo "🔐 Setting up Let's Encrypt SSL certificates for $DOMAIN..."

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
    
    # Install certbot based on OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y certbot python3-certbot-nginx
        elif command -v yum &> /dev/null; then
            sudo yum install -y certbot python3-certbot-nginx
        else
            echo "❌ Unsupported Linux distribution. Please install certbot manually."
            exit 1
        fi
    else
        echo "❌ Unsupported OS. Please install certbot manually."
        exit 1
    fi
fi

# Create SSL directory
mkdir -p "$SSL_DIR"

# Stop nginx if running
echo "🛑 Stopping nginx..."
sudo systemctl stop nginx 2>/dev/null || docker-compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true

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

# Generate default certificate for catch-all server
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/default.key" \
    -out "$SSL_DIR/default.crt" \
    -subj "/C=US/ST=State/L=City/O=Default/CN=default"

chmod 600 "$SSL_DIR/default.key"
chmod 644 "$SSL_DIR/default.crt"

echo "✅ Let's Encrypt certificates installed successfully!"
echo "📁 Certificates location: $SSL_DIR"
echo ""
echo "🔄 Setting up automatic renewal..."

# Setup automatic renewal
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --deploy-hook 'docker-compose -f $(pwd)/docker-compose.prod.yml restart nginx'") | crontab -

echo "✅ Automatic renewal configured!"
echo ""
echo "🚀 You can now start your services:"
echo "   docker-compose -f docker-compose.prod.yml up -d"