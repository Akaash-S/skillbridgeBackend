#!/bin/bash
# SkillBridge Backend - Production GCE Startup Script
# This script automates the full setup of a fresh GCE VM instance.

set -e

# Log everything to syslog for debugging
exec 1> >(logger -s -t $(basename $0)) 2>&1

echo "🚀 Starting SkillBridge Backend Production Setup..."

# 1. Configuration Constants
APP_DIR="/opt/skillbridge/backend"
LOG_DIR="/opt/skillbridge/logs"
USER_NAME="skillbridge"
DOCKER_COMPOSE_VERSION="v2.24.1"

# 2. System Updates & Essential Tools
echo "📦 Updating system and installing essentials..."
apt-get update
apt-get upgrade -y
apt-get install -y \
    curl git wget unzip nginx fail2ban ufw certbot python3-certbot-nginx \
    apt-transport-https ca-certificates gnupg lsb-release

# 3. Docker Installation
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

# Ensure docker-compose is available as a command if plugin isn't enough for some scripts
if ! command -v docker-compose &> /dev/null; then
    ln -s /usr/libexec/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose || true
fi

systemctl enable docker
systemctl start docker

# 4. User & Directory Setup
echo "👤 Setting up application user..."
if ! id -u $USER_NAME >/dev/null 2>&1; then
    useradd -m -s /bin/bash $USER_NAME
    usermod -aG docker $USER_NAME
fi

mkdir -p $APP_DIR $LOG_DIR
chown -R $USER_NAME:$USER_NAME /opt/skillbridge

# 5. Security - Firewall (UFW)
echo "🛡️ Configuring Firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# 6. Nginx Configuration
echo "🌐 Configuring Nginx Reverse Proxy..."
mkdir -p /etc/nginx/conf.d

# Write global shared rate limiting configuration (in http context)
echo "Creating global rate limiting zones in /etc/nginx/conf.d/rate_limits.conf..."
cat > /etc/nginx/conf.d/rate_limits.conf << 'EOF'
# SkillBridge Rate Limiting Zones (Shared globally in http block)
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;
EOF

# Clean up any duplicate definitions from main nginx.conf and sites-available
echo "Cleaning up duplicate rate limiting zones..."
if [ -f /etc/nginx/nginx.conf ]; then
    sed -i '/limit_req_zone/d' /etc/nginx/nginx.conf
fi
for f in /etc/nginx/sites-available/*; do
    if [ -f "$f" ]; then
        sed -i '/limit_req_zone/d' "$f"
    fi
done

cat > /etc/nginx/sites-available/skillbridge << 'EOF'
server {
    listen 80;
    server_name _; # Will be updated if domain is provided

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location = /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
        access_log off;
    }
}
EOF

ln -sf /etc/nginx/sites-available/skillbridge /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
echo "Testing Nginx configuration..."
if nginx -t; then
    echo "Nginx configuration is valid."
    systemctl enable nginx
    systemctl restart nginx
else
    echo "Nginx configuration test failed!"
    exit 1
fi

# 7. Application Deployment (Initial)
# Note: The actual code pull/deployment is often handled by the local script 
# pushing code or via git clone if a repo is public. 
# Here we prepare the directory.
echo "📂 Application directory ready at $APP_DIR"

# 8. Success Signal
echo "✅ Startup script completed successfully!"
