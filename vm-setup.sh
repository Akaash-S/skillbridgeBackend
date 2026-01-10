#!/bin/bash

# SkillBridge Backend - VM Setup Script for Google Compute Engine
# This script sets up a production-ready environment on a GCP VM

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run this script as root (use sudo)"
    exit 1
fi

print_info "Setting up SkillBridge Backend on Google Compute Engine VM..."

# Update system packages
print_info "Updating system packages..."
apt-get update -y
apt-get upgrade -y

# Install essential packages
print_info "Installing essential packages..."
apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    htop \
    nano \
    vim

# Install Docker
print_info "Installing Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Install Docker Compose
print_info "Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Google Cloud SDK
print_info "Installing Google Cloud SDK..."
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
apt-get update -y
apt-get install -y google-cloud-sdk

# Install Nginx
print_info "Installing and configuring Nginx..."
apt-get install -y nginx

# Configure firewall
print_info "Configuring firewall..."
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8080/tcp  # For backend service

# Configure fail2ban
print_info "Configuring fail2ban..."
systemctl start fail2ban
systemctl enable fail2ban

# Create application user
print_info "Creating application user..."
useradd -m -s /bin/bash skillbridge
usermod -aG docker skillbridge

# Create application directories
print_info "Creating application directories..."
mkdir -p /opt/skillbridge
mkdir -p /opt/skillbridge/backend
mkdir -p /opt/skillbridge/logs
mkdir -p /opt/skillbridge/ssl
mkdir -p /opt/skillbridge/backups
chown -R skillbridge:skillbridge /opt/skillbridge

# Create systemd service for the application
print_info "Creating systemd service..."
cat > /etc/systemd/system/skillbridge-backend.service << 'EOF'
[Unit]
Description=SkillBridge Backend Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/skillbridge/backend
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=skillbridge
Group=skillbridge

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
systemctl daemon-reload
systemctl enable skillbridge-backend

# Configure log rotation
print_info "Configuring log rotation..."
cat > /etc/logrotate.d/skillbridge << 'EOF'
/opt/skillbridge/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 skillbridge skillbridge
    postrotate
        docker-compose -f /opt/skillbridge/backend/docker-compose.yml restart > /dev/null 2>&1 || true
    endscript
}
EOF

# Create backup script
print_info "Creating backup script..."
cat > /opt/skillbridge/backup.sh << 'EOF'
#!/bin/bash
# SkillBridge Backup Script

BACKUP_DIR="/opt/skillbridge/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="skillbridge_backup_$DATE.tar.gz"

# Create backup
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
    --exclude="$BACKUP_DIR" \
    --exclude="/opt/skillbridge/logs" \
    /opt/skillbridge/

# Keep only last 7 backups
cd "$BACKUP_DIR"
ls -t skillbridge_backup_*.tar.gz | tail -n +8 | xargs -r rm

echo "Backup created: $BACKUP_FILE"
EOF

chmod +x /opt/skillbridge/backup.sh
chown skillbridge:skillbridge /opt/skillbridge/backup.sh

# Add backup to crontab
print_info "Setting up automated backups..."
(crontab -u skillbridge -l 2>/dev/null; echo "0 2 * * * /opt/skillbridge/backup.sh") | crontab -u skillbridge -

# Configure Nginx as reverse proxy
print_info "Configuring Nginx..."
cat > /etc/nginx/sites-available/skillbridge << 'EOF'
server {
    listen 80;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # Client max body size
    client_max_body_size 10M;
    
    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        access_log off;
    }
    
    # Auth endpoints (stricter rate limiting)
    location /auth/ {
        limit_req zone=auth burst=10 nodelay;
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API endpoints
    location / {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type, Accept" always;
        add_header Access-Control-Allow-Credentials "true" always;
        
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin "*";
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "Authorization, Content-Type, Accept";
            add_header Access-Control-Allow-Credentials "true";
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
    }
}
EOF

# Enable the site
ln -sf /etc/nginx/sites-available/skillbridge /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t

# Start and enable Nginx
systemctl start nginx
systemctl enable nginx

# Create monitoring script
print_info "Creating monitoring script..."
cat > /opt/skillbridge/monitor.sh << 'EOF'
#!/bin/bash
# SkillBridge Monitoring Script

LOG_FILE="/opt/skillbridge/logs/monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Check if backend service is running
if ! docker-compose -f /opt/skillbridge/backend/docker-compose.yml ps | grep -q "Up"; then
    echo "[$DATE] ERROR: Backend service is not running" >> $LOG_FILE
    # Restart the service
    systemctl restart skillbridge-backend
    echo "[$DATE] INFO: Attempted to restart backend service" >> $LOG_FILE
fi

# Check if Nginx is running
if ! systemctl is-active --quiet nginx; then
    echo "[$DATE] ERROR: Nginx is not running" >> $LOG_FILE
    systemctl restart nginx
    echo "[$DATE] INFO: Attempted to restart Nginx" >> $LOG_FILE
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "[$DATE] WARNING: Disk usage is at ${DISK_USAGE}%" >> $LOG_FILE
fi

# Check memory usage
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ $MEMORY_USAGE -gt 80 ]; then
    echo "[$DATE] WARNING: Memory usage is at ${MEMORY_USAGE}%" >> $LOG_FILE
fi

echo "[$DATE] INFO: Health check completed" >> $LOG_FILE
EOF

chmod +x /opt/skillbridge/monitor.sh
chown skillbridge:skillbridge /opt/skillbridge/monitor.sh

# Add monitoring to crontab (every 5 minutes)
(crontab -u skillbridge -l 2>/dev/null; echo "*/5 * * * * /opt/skillbridge/monitor.sh") | crontab -u skillbridge -

# Create deployment script for the application
print_info "Creating deployment script..."
cat > /opt/skillbridge/deploy-app.sh << 'EOF'
#!/bin/bash
# SkillBridge Application Deployment Script

set -e

REPO_URL="https://github.com/your-username/skillbridge.git"
BRANCH="main"
APP_DIR="/opt/skillbridge/backend"

print_info() {
    echo -e "\033[0;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

# Stop the current service
print_info "Stopping current service..."
systemctl stop skillbridge-backend || true

# Backup current deployment
if [ -d "$APP_DIR" ]; then
    print_info "Backing up current deployment..."
    cp -r "$APP_DIR" "/opt/skillbridge/backups/backend_$(date +%Y%m%d_%H%M%S)"
fi

# Clone or update repository
if [ -d "$APP_DIR/.git" ]; then
    print_info "Updating existing repository..."
    cd "$APP_DIR"
    git fetch origin
    git reset --hard origin/$BRANCH
else
    print_info "Cloning repository..."
    rm -rf "$APP_DIR"
    git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# Copy environment file if it doesn't exist
if [ ! -f "$APP_DIR/.env" ]; then
    print_info "Creating environment file..."
    cp "$APP_DIR/.env.gcp" "$APP_DIR/.env"
    print_error "Please update $APP_DIR/.env with your actual values"
fi

# Build and start the application
print_info "Building and starting application..."
docker-compose build --no-cache
systemctl start skillbridge-backend

# Wait for service to be ready
print_info "Waiting for service to be ready..."
sleep 30

# Health check
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    print_success "Deployment successful! Service is healthy."
else
    print_error "Deployment may have issues. Check logs with: docker-compose logs"
fi
EOF

chmod +x /opt/skillbridge/deploy-app.sh
chown skillbridge:skillbridge /opt/skillbridge/deploy-app.sh

# Install SSL certificate tool (Certbot)
print_info "Installing Certbot for SSL certificates..."
apt-get install -y certbot python3-certbot-nginx

print_success "VM setup completed successfully!"
print_info ""
print_info "Next steps:"
print_info "1. Deploy your application: sudo -u skillbridge /opt/skillbridge/deploy-app.sh"
print_info "2. Update environment variables in /opt/skillbridge/backend/.env"
print_info "3. Set up SSL certificate: certbot --nginx -d your-domain.com"
print_info "4. Configure DNS to point to this VM's external IP"
print_info ""
print_info "Useful commands:"
print_info "- Check service status: systemctl status skillbridge-backend"
print_info "- View logs: docker-compose -f /opt/skillbridge/backend/docker-compose.yml logs"
print_info "- Monitor system: /opt/skillbridge/monitor.sh"
print_info "- Create backup: /opt/skillbridge/backup.sh"
print_info ""
print_info "The system is now ready for production deployment!"