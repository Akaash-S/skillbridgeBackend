#!/bin/bash

# Quick script to edit .env configuration file
# This makes it easy for users to configure their environment

echo "🔧 Opening .env configuration file..."
echo ""
echo "📝 Please update the following required values:"
echo "   - SECRET_KEY (generate a secure random key)"
echo "   - DOMAIN (your actual domain name)"
echo "   - SSL_EMAIL (your email for SSL certificates)"
echo "   - FIREBASE_SERVICE_ACCOUNT_BASE64"
echo "   - API keys (Gemini, YouTube, etc.)"
echo "   - Email settings (SMTP credentials)"
echo "   - REDIS_PASSWORD"
echo "   - CORS_ORIGINS (your frontend domain)"
echo ""
echo "💡 Tip: Use Ctrl+X, then Y, then Enter to save and exit"
echo ""
read -p "Press Enter to open the .env file for editing..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found in current directory"
    echo "   Make sure you're in the /opt/skillbridge/backend directory"
    exit 1
fi

# Open .env file with nano (most user-friendly)
nano .env

echo ""
echo "✅ Configuration file updated!"
echo ""
echo "🚀 Next steps:"
echo "   1. Run the continuation script: ./continue-deployment.sh"
echo "   2. Or restart if already deployed: docker-compose restart"
echo ""