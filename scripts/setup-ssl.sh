#!/bin/bash
# SkillBridge Consolidated SSL Setup Script
# Usage:
#   ./scripts/setup-ssl.sh [letsencrypt | self-signed] [domain] [email]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

MODE=${1:-letsencrypt}
DOMAIN=${2:-"skillbridge-server.asolvitra.tech"}
EMAIL=${3:-"admin@asolvitra.tech"}
SSL_DIR="./nginx/ssl"

mkdir -p "$SSL_DIR"

case "$MODE" in
    self-signed)
        echo "🔐 Generating Self-Signed SSL Certificate for $DOMAIN..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$SSL_DIR/privkey.pem" \
            -out "$SSL_DIR/fullchain.pem" \
            -subj "/C=US/ST=State/L=City/O=SkillBridge/CN=$DOMAIN"
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$SSL_DIR/default.key" \
            -out "$SSL_DIR/default.crt" \
            -subj "/C=US/ST=State/L=City/O=Default/CN=default"

        chmod 600 "$SSL_DIR/privkey.pem" "$SSL_DIR/default.key"
        chmod 644 "$SSL_DIR/fullchain.pem" "$SSL_DIR/default.crt"
        echo "✅ Self-signed certificates successfully placed in $SSL_DIR"
        ;;

    letsencrypt)
        echo "🔐 Configuring Let's Encrypt SSL Certificates for $DOMAIN..."
        
        if ! command -v certbot &> /dev/null; then
            echo "📦 Installing certbot..."
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y certbot python3-certbot-nginx
            else
                echo "❌ Certbot not found and apt-get unavailable. Please install certbot manually."
                exit 1
            fi
        fi

        echo "🛑 Stopping nginx temporarily for certbot verification..."
        sudo systemctl stop nginx 2>/dev/null || docker-compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true

        echo "📜 Requesting certificate from Let's Encrypt..."
        sudo certbot certonly \
            --standalone \
            --email "$EMAIL" \
            --agree-tos \
            --no-eff-email \
            --domains "$DOMAIN" \
            --non-interactive

        echo "📋 Copying certificates to $SSL_DIR..."
        sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/"
        sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/"
        sudo cp "/etc/letsencrypt/live/$DOMAIN/chain.pem" "$SSL_DIR/" 2>/dev/null || true
        sudo chown $(whoami):$(whoami) "$SSL_DIR"/*.pem 2>/dev/null || true
        chmod 600 "$SSL_DIR"/*.pem

        # Default fallback cert
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$SSL_DIR/default.key" \
            -out "$SSL_DIR/default.crt" \
            -subj "/C=US/ST=State/L=City/O=Default/CN=default" 2>/dev/null || true

        echo "🔄 Installing daily auto-renewal cron..."
        (crontab -l 2>/dev/null | grep -v 'certbot renew'; echo "0 12 * * * /usr/bin/certbot renew --quiet --deploy-hook 'docker-compose -f $ROOT_DIR/docker-compose.prod.yml restart nginx 2>/dev/null || systemctl reload nginx'") | crontab -

        echo "✅ Let's Encrypt SSL setup and auto-renewal complete!"
        ;;

    *)
        echo "❌ Invalid mode. Usage: ./scripts/setup-ssl.sh [letsencrypt | self-signed]"
        exit 1
        ;;
esac
