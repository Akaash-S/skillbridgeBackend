#!/bin/bash

# Generate self-signed SSL certificates for development/testing
# For production, use Let's Encrypt or proper CA certificates

set -e

DOMAIN="skillbridge-server.asolvitra.tech"
SSL_DIR="./nginx/ssl"

echo "🔐 Generating SSL certificates for $DOMAIN..."

# Create SSL directory if it doesn't exist
mkdir -p "$SSL_DIR"

# Generate private key
openssl genrsa -out "$SSL_DIR/privkey.pem" 2048

# Generate certificate signing request
openssl req -new -key "$SSL_DIR/privkey.pem" -out "$SSL_DIR/cert.csr" -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"

# Generate self-signed certificate
openssl x509 -req -in "$SSL_DIR/cert.csr" -signkey "$SSL_DIR/privkey.pem" -out "$SSL_DIR/fullchain.pem" -days 365

# Create chain file (same as fullchain for self-signed)
cp "$SSL_DIR/fullchain.pem" "$SSL_DIR/chain.pem"

# Generate default certificate for catch-all server
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/default.key" \
    -out "$SSL_DIR/default.crt" \
    -subj "/C=US/ST=State/L=City/O=Default/CN=default"

# Set proper permissions
chmod 600 "$SSL_DIR"/*.pem "$SSL_DIR"/*.key
chmod 644 "$SSL_DIR"/*.crt

echo "✅ SSL certificates generated successfully!"
echo "📁 Certificates location: $SSL_DIR"
echo ""
echo "⚠️  IMPORTANT: These are self-signed certificates for development only!"
echo "   For production, use Let's Encrypt or proper CA certificates."
echo ""
echo "🚀 To use Let's Encrypt in production, run:"
echo "   ./scripts/setup-letsencrypt.sh"