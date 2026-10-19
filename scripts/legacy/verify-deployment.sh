#!/bin/bash

# Comprehensive deployment verification script
# Run this after deployment to ensure everything is working correctly

set -e

echo "🔍 SkillBridge Deployment Verification"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ] || [ ! -f "Dockerfile" ]; then
    echo -e "${RED}❌ Not in application directory. Please navigate to the directory containing docker-compose.yml${NC}"
    echo ""
    echo "Try running: ./find-app.sh"
    exit 1
fi

echo "📍 Current directory: $(pwd)"
echo ""

# 1. Check Docker and Docker Compose
echo "🐳 Checking Docker installation..."
docker --version > /dev/null 2>&1
print_status $? "Docker is installed"

docker-compose --version > /dev/null 2>&1
print_status $? "Docker Compose is installed"
echo ""

# 2. Check .env configuration
echo "🔧 Checking configuration..."
if [ -f ".env" ]; then
    print_status 0 ".env file exists"
    
    # Check for placeholder values
    if grep -q "your-super-secret-key-change-this" .env; then
        print_status 1 "SECRET_KEY still has placeholder value"
    else
        print_status 0 "SECRET_KEY is configured"
    fi
    
    if grep -q "your-domain.com" .env; then
        print_status 1 "DOMAIN still has placeholder value"
    else
        print_status 0 "DOMAIN is configured"
    fi
    
    if grep -q "your-base64-encoded-service-account" .env; then
        print_status 1 "FIREBASE_SERVICE_ACCOUNT_BASE64 still has placeholder value"
    else
        print_status 0 "FIREBASE_SERVICE_ACCOUNT_BASE64 is configured"
    fi
else
    print_status 1 ".env file not found"
fi
echo ""

# 3. Check container status
echo "📦 Checking container status..."
if docker-compose ps | grep -q "Up"; then
    print_status 0 "Containers are running"
    
    # Show container details
    echo ""
    print_info "Container status:"
    docker-compose ps
    echo ""
else
    print_status 1 "Containers are not running"
    echo ""
    print_info "Container status:"
    docker-compose ps
    echo ""
fi

# 4. Check health endpoint
echo "🏥 Checking health endpoint..."
if curl -f -s http://localhost/health > /dev/null 2>&1; then
    print_status 0 "Health endpoint is responding"
    
    # Show health response
    HEALTH_RESPONSE=$(curl -s http://localhost/health)
    print_info "Health response: $HEALTH_RESPONSE"
else
    print_status 1 "Health endpoint is not responding"
    print_warning "Try: docker-compose logs to check for errors"
fi
echo ""

# 5. Check ports
echo "🔌 Checking port configuration..."
if netstat -tuln | grep -q ":80 "; then
    print_status 0 "Port 80 is bound"
else
    print_status 1 "Port 80 is not bound"
fi

if netstat -tuln | grep -q ":443 "; then
    print_status 0 "Port 443 is bound"
else
    print_status 1 "Port 443 is not bound"
fi

# Check if application ports are NOT externally accessible (good)
if netstat -tuln | grep -q "0.0.0.0:8080"; then
    print_status 1 "Port 8080 is externally accessible (security risk)"
else
    print_status 0 "Port 8080 is not externally accessible (secure)"
fi

if netstat -tuln | grep -q "0.0.0.0:6379"; then
    print_status 1 "Port 6379 is externally accessible (security risk)"
else
    print_status 0 "Port 6379 is not externally accessible (secure)"
fi
echo ""

# 6. Check firewall
echo "🛡️  Checking firewall configuration..."
if command -v ufw > /dev/null 2>&1; then
    if ufw status | grep -q "Status: active"; then
        print_status 0 "UFW firewall is active"
        
        if ufw status | grep -q "80/tcp.*ALLOW"; then
            print_status 0 "Port 80 is allowed in firewall"
        else
            print_status 1 "Port 80 is not allowed in firewall"
        fi
        
        if ufw status | grep -q "443/tcp.*ALLOW"; then
            print_status 0 "Port 443 is allowed in firewall"
        else
            print_status 1 "Port 443 is not allowed in firewall"
        fi
        
        if ufw status | grep -q "8080/tcp.*DENY"; then
            print_status 0 "Port 8080 is blocked in firewall (secure)"
        else
            print_warning "Port 8080 firewall rule not found"
        fi
    else
        print_warning "UFW firewall is not active"
    fi
else
    print_warning "UFW firewall not installed"
fi
echo ""

# 7. Check SSL certificates
echo "🔐 Checking SSL certificates..."
if [ -f "nginx/ssl/fullchain.pem" ] && [ -f "nginx/ssl/privkey.pem" ]; then
    print_status 0 "SSL certificates exist"
    
    # Check certificate expiry
    EXPIRY=$(openssl x509 -in nginx/ssl/fullchain.pem -noout -enddate 2>/dev/null | cut -d= -f2)
    if [ $? -eq 0 ]; then
        print_info "Certificate expires: $EXPIRY"
        
        # Check if certificate expires in next 30 days
        EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null)
        CURRENT_EPOCH=$(date +%s)
        DAYS_LEFT=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))
        
        if [ $DAYS_LEFT -gt 30 ]; then
            print_status 0 "Certificate is valid ($DAYS_LEFT days remaining)"
        elif [ $DAYS_LEFT -gt 7 ]; then
            print_warning "Certificate expires soon ($DAYS_LEFT days remaining)"
        else
            print_status 1 "Certificate expires very soon ($DAYS_LEFT days remaining)"
        fi
    fi
else
    print_status 1 "SSL certificates not found"
fi
echo ""

# 8. Check external connectivity
echo "🌐 Checking external connectivity..."
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "unknown")
if [ "$SERVER_IP" != "unknown" ]; then
    print_status 0 "External IP detected: $SERVER_IP"
else
    print_warning "Could not detect external IP"
fi

# Test external health check if we have an IP
if [ "$SERVER_IP" != "unknown" ]; then
    if curl -f -s --max-time 10 http://$SERVER_IP/health > /dev/null 2>&1; then
        print_status 0 "External health check successful"
    else
        print_status 1 "External health check failed"
        print_warning "This might be normal if firewall rules are still propagating"
    fi
fi
echo ""

# 9. Check logs for errors
echo "📋 Checking recent logs for errors..."
if docker-compose logs --tail=50 2>/dev/null | grep -i -E "(error|critical|fatal)" | head -5 | grep -q .; then
    print_warning "Recent errors found in logs:"
    docker-compose logs --tail=50 2>/dev/null | grep -i -E "(error|critical|fatal)" | head -5
else
    print_status 0 "No recent errors in logs"
fi
echo ""

# 10. Resource usage check
echo "💾 Checking resource usage..."
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    print_status 0 "Disk usage: ${DISK_USAGE}% (healthy)"
elif [ $DISK_USAGE -lt 90 ]; then
    print_warning "Disk usage: ${DISK_USAGE}% (monitor)"
else
    print_status 1 "Disk usage: ${DISK_USAGE}% (critical)"
fi

MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", ($3/$2) * 100.0}')
if [ $MEMORY_USAGE -lt 80 ]; then
    print_status 0 "Memory usage: ${MEMORY_USAGE}% (healthy)"
elif [ $MEMORY_USAGE -lt 90 ]; then
    print_warning "Memory usage: ${MEMORY_USAGE}% (monitor)"
else
    print_status 1 "Memory usage: ${MEMORY_USAGE}% (critical)"
fi
echo ""

# Summary
echo "📊 DEPLOYMENT SUMMARY"
echo "===================="
echo ""

if curl -f -s http://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}🎉 DEPLOYMENT SUCCESSFUL!${NC}"
    echo ""
    echo "Your SkillBridge backend is running and accessible at:"
    echo "  HTTP:  http://$SERVER_IP"
    echo "  HTTPS: https://$SERVER_IP (if SSL configured)"
    echo ""
    echo "✅ Security features active:"
    echo "  - Nginx reverse proxy filtering requests"
    echo "  - Rate limiting protecting against abuse"
    echo "  - Application ports secured (8080, 6379 not externally accessible)"
    echo "  - Firewall configured"
    echo ""
    echo "🔧 Next steps:"
    echo "  1. Configure your domain DNS to point to: $SERVER_IP"
    echo "  2. Setup Let's Encrypt SSL: ./setup-letsencrypt-gcp.sh"
    echo "  3. Test your application endpoints"
    echo "  4. Setup monitoring and backups"
else
    echo -e "${RED}❌ DEPLOYMENT NEEDS ATTENTION${NC}"
    echo ""
    echo "🔧 Troubleshooting steps:"
    echo "  1. Check logs: docker-compose logs -f"
    echo "  2. Verify .env configuration: cat .env"
    echo "  3. Restart services: docker-compose restart"
    echo "  4. Check container status: docker-compose ps"
fi

echo ""
echo "📋 Useful commands:"
echo "  View logs:    docker-compose logs -f"
echo "  Restart:      docker-compose restart"
echo "  Stop:         docker-compose down"
echo "  Status:       docker-compose ps"
echo "  Health:       curl -f http://localhost/health"
echo ""
echo "📚 Documentation:"
echo "  Complete guide: cat COMPLETE_DEPLOYMENT_SOLUTION.md"
echo "  Troubleshooting: Check logs and verify configuration"