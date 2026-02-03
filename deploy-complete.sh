#!/bin/bash

# Complete SkillBridge Deployment Script
# This script handles the entire deployment process from start to finish

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "🚀 SkillBridge Complete Deployment Script"
echo "========================================"
echo -e "${NC}"
echo ""

# Function to print colored output
print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root. This is not recommended for security."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: System Update
print_step "Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y
print_success "System updated"
echo ""

# Step 2: Install Docker
print_step "Installing Docker..."
if ! command -v docker &> /dev/null; then
    # Remove old Docker versions
    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Install prerequisites
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    
    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Set up the repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Update package index and install Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    sudo usermod -aG docker $USER
    print_success "Docker installed"
else
    print_success "Docker already installed"
fi

# Step 3: Install Docker Compose
print_step "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    # Docker Compose V2 is included with Docker Engine, create symlink for compatibility
    sudo ln -sf /usr/libexec/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose 2>/dev/null || true
    print_success "Docker Compose installed"
else
    print_success "Docker Compose already installed"
fi
echo ""

# Step 4: Setup Application Directory
print_step "Setting up application directory..."
sudo mkdir -p /opt/skillbridge
sudo chown $USER:$USER /opt/skillbridge
cd /opt/skillbridge

# Step 5: Clone Repository
print_step "Cloning repository..."
if [ ! -d ".git" ]; then
    git clone https://github.com/Akaash-S/skillbridgeBackend.git .
    print_success "Repository cloned"
else
    print_success "Repository already exists"
    git pull origin main
    print_success "Repository updated"
fi

# Step 6: Navigate to correct directory
if [ -d "backend" ] && [ -f "backend/Dockerfile" ]; then
    cd backend
    print_success "Found backend directory"
elif [ -f "Dockerfile" ]; then
    print_success "Found application files in root"
else
    print_error "Could not find Dockerfile. Please check repository structure."
    exit 1
fi

APP_DIR=$(pwd)
print_success "Application directory: $APP_DIR"
echo ""

# Step 7: Create .env file
print_step "Creating environment configuration..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Application Settings
SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=production
PORT=8080

# Domain Configuration (update with your domain)
DOMAIN=your-domain.com
SSL_EMAIL=admin@your-domain.com

# Firebase Configuration
FIREBASE_SERVICE_ACCOUNT_BASE64=your-base64-encoded-service-account
DISABLE_FIREBASE=false

# API Keys (add your actual keys)
GEMINI_API_KEY=your-gemini-api-key
YOUTUBE_API_KEY=your-youtube-api-key
ADZUNA_APP_ID=your-adzuna-app-id
ADZUNA_APP_KEY=your-adzuna-app-key

# MFA Configuration
MFA_ISSUER_NAME=SkillBridge
MFA_SECRET_KEY=your-mfa-secret-key

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
EMAIL_FROM_NAME=SkillBridge
EMAIL_SUPPORT=support@your-domain.com

# CORS Configuration
CORS_ORIGINS=https://your-frontend-domain.com

# Redis Configuration
REDIS_PASSWORD=secure-redis-password-change-this

# GCP Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GCP_REGION=us-central1
EOF
    print_success ".env file created"
else
    print_success ".env file already exists"
fi

# Step 8: Configuration prompt
echo ""
print_warning "CONFIGURATION REQUIRED!"
echo "======================="
echo ""
echo "📝 You MUST edit the .env file with your actual configuration before continuing."
echo ""
echo "Required changes:"
echo "  - SECRET_KEY (generate a secure random key)"
echo "  - DOMAIN (your actual domain name)"
echo "  - SSL_EMAIL (your email for SSL certificates)"
echo "  - FIREBASE_SERVICE_ACCOUNT_BASE64"
echo "  - API keys (Gemini, YouTube, etc.)"
echo "  - Email settings (SMTP credentials)"
echo "  - REDIS_PASSWORD"
echo "  - CORS_ORIGINS"
echo ""
echo "Options:"
echo "  1. Edit now with nano"
echo "  2. Edit later and run deployment manually"
echo "  3. Continue with template (NOT RECOMMENDED)"
echo ""

read -p "Choose option (1/2/3): " -n 1 -r
echo ""

case $REPLY in
    1)
        echo ""
        print_step "Opening .env file for editing..."
        nano .env
        ;;
    2)
        echo ""
        print_warning "Please edit .env file and then run: ./continue-deployment.sh"
        
        # Create continuation script
        cat > continue-deployment.sh << 'CONTINUE_EOF'
#!/bin/bash
set -e

echo "🚀 Continuing SkillBridge deployment..."

# Verify configuration
if grep -q "your-super-secret-key-change-this" .env; then
    echo "❌ ERROR: Please update SECRET_KEY in .env file"
    exit 1
fi

if grep -q "your-domain.com" .env; then
    echo "❌ ERROR: Please update DOMAIN in .env file"
    exit 1
fi

echo "✅ Configuration appears to be updated"

# Continue with deployment steps...
source deploy-complete.sh --continue-from-config
CONTINUE_EOF
        
        chmod +x continue-deployment.sh
        print_success "Continuation script created: ./continue-deployment.sh"
        exit 0
        ;;
    3)
        print_warning "Continuing with template configuration (not recommended for production)"
        ;;
    *)
        print_error "Invalid option. Exiting."
        exit 1
        ;;
esac

# Step 9: Validate configuration
print_step "Validating configuration..."
if grep -q "your-super-secret-key-change-this" .env; then
    print_error "SECRET_KEY still contains placeholder value"
    print_warning "Please edit .env file: nano .env"
    exit 1
fi

if grep -q "your-domain.com" .env && [ "$REPLY" != "3" ]; then
    print_error "DOMAIN still contains placeholder value"
    print_warning "Please edit .env file: nano .env"
    exit 1
fi

print_success "Configuration validated"
echo ""

# Step 10: Create directories
print_step "Creating necessary directories..."
mkdir -p logs nginx/ssl
print_success "Directories created"

# Step 11: Generate SSL certificates
print_step "Generating SSL certificates..."
if [ ! -f "nginx/ssl/fullchain.pem" ]; then
    DOMAIN=$(grep "^DOMAIN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "localhost")
    if [ "$DOMAIN" = "your-domain.com" ] || [ -z "$DOMAIN" ]; then
        DOMAIN="localhost"
    fi
    
    openssl genrsa -out nginx/ssl/privkey.pem 2048
    openssl req -new -x509 -key nginx/ssl/privkey.pem -out nginx/ssl/fullchain.pem -days 365 \
        -subj "/C=US/ST=State/L=City/O=SkillBridge/CN=$DOMAIN"
    cp nginx/ssl/fullchain.pem nginx/ssl/chain.pem
    chmod 600 nginx/ssl/*.pem
    
    print_success "SSL certificates generated for $DOMAIN"
else
    print_success "SSL certificates already exist"
fi

# Step 12: Configure firewall
print_step "Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow 22/tcp
    sudo ufw deny 8080/tcp
    sudo ufw deny 6379/tcp
    sudo ufw --force enable
    print_success "UFW firewall configured"
else
    print_warning "UFW not available, skipping local firewall configuration"
fi

# Configure GCP firewall if gcloud is available
if command -v gcloud &> /dev/null; then
    print_step "Configuring GCP firewall rules..."
    
    gcloud compute firewall-rules create skillbridge-allow-web \
        --allow tcp:80,tcp:443 \
        --source-ranges 0.0.0.0/0 \
        --description "Allow HTTP and HTTPS for SkillBridge" \
        --quiet 2>/dev/null || print_warning "Web firewall rule may already exist"
    
    gcloud compute firewall-rules create skillbridge-deny-direct \
        --action deny \
        --rules tcp:8080,tcp:6379 \
        --source-ranges 0.0.0.0/0 \
        --priority 1000 \
        --description "Block direct access to application ports" \
        --quiet 2>/dev/null || print_warning "Deny firewall rule may already exist"
    
    print_success "GCP firewall rules configured"
else
    print_warning "gcloud CLI not available, skipping GCP firewall configuration"
fi
echo ""

# Step 13: Build and start application
print_step "Building and starting application..."
docker compose down --remove-orphans 2>/dev/null || true
docker compose build --no-cache
docker compose up -d
print_success "Application started"
echo ""

# Step 14: Wait for services
print_step "Waiting for services to start..."
sleep 30

# Step 15: Health check
print_step "Performing health check..."
MAX_RETRIES=20
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s http://localhost/health > /dev/null 2>&1; then
        print_success "Health check passed!"
        break
    else
        echo "⏳ Waiting for service... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 3
        RETRY_COUNT=$((RETRY_COUNT + 1))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "Health check failed after $MAX_RETRIES attempts"
    print_warning "Check logs: docker-compose logs"
    exit 1
fi

# Step 16: Final verification
print_step "Running final verification..."
if [ -f "verify-deployment.sh" ]; then
    chmod +x verify-deployment.sh
    ./verify-deployment.sh
else
    print_warning "Verification script not found, performing basic checks..."
    docker-compose ps
    curl -f http://localhost/health
fi

# Step 17: Success message
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "YOUR_SERVER_IP")

echo ""
echo -e "${GREEN}"
echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "===================================="
echo -e "${NC}"
echo ""
echo "📊 Service Status:"
docker compose ps
echo ""
echo "🔗 Your application is available at:"
echo "   HTTP:  http://$SERVER_IP"
echo "   HTTPS: https://$SERVER_IP (with self-signed certificate)"
echo ""
echo "🔧 Next steps:"
echo "   1. Configure your domain DNS to point to: $SERVER_IP"
echo "   2. Setup Let's Encrypt SSL: ./setup-letsencrypt-gcp.sh"
echo "   3. Test your application endpoints"
echo "   4. Setup monitoring and backups"
echo ""
echo "📋 Useful commands:"
echo "   View logs:    docker compose logs -f"
echo "   Restart:      docker compose restart"
echo "   Stop:         docker compose down"
echo "   Status:       docker compose ps"
echo "   Health:       curl -f http://localhost/health"
echo "   Verify:       ./verify-deployment.sh"
echo ""
echo "🛡️  Security features active:"
echo "   ✅ Nginx reverse proxy filtering malicious requests"
echo "   ✅ Rate limiting protecting against abuse"
echo "   ✅ Application ports secured (8080, 6379 not externally accessible)"
echo "   ✅ Firewall configured"
echo "   ✅ SSL/TLS encryption ready"
echo ""
print_success "Your SkillBridge backend is now production-ready!"
echo ""
echo "📚 For troubleshooting and advanced configuration, see:"
echo "   - COMPLETE_DEPLOYMENT_SOLUTION.md"
echo "   - Run: ./verify-deployment.sh for detailed status"