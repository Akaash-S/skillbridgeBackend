#!/bin/bash
# SkillBridge Backend - GCE One-Click Deployment Script
# This script provisions infrastructure and deploys the backend.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# 1. Configuration (Editable)
PROJECT_ID=$(gcloud config get-value project)
INSTANCE_NAME="skillbridge-backend-prod"
ZONE="us-central1-a"
MACHINE_TYPE="e2-medium" # 2 vCPU, 4GB RAM - recommended for production
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"
STATIC_IP_NAME="skillbridge-backend-ip"

echo -e "${BLUE}==========================================================${NC}"
echo -e "${BLUE}   SkillBridge Backend - GCE One-Click Deployer         ${NC}"
echo -e "${BLUE}==========================================================${NC}"

# Check for gcloud
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

if [ -z "$PROJECT_ID" ]; then
    print_error "No GCP project selected. Run: gcloud config set project [PROJECT_ID]"
    exit 1
fi

print_status "Deploying to project: $PROJECT_ID"

# 2. Check for required local files
if [ ! -f "Dockerfile" ] || [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the 'backend' directory."
    exit 1
fi

if [ ! -f ".env" ]; then
    print_warning ".env file not found. Deployment will proceed but service may fail."
    echo "It is highly recommended to have a .env file with production secrets."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi
fi

# 3. Reserve Static External IP (if not exists)
if ! gcloud compute addresses describe $STATIC_IP_NAME --region ${ZONE%-*} &>/dev/null; then
    print_status "Reserving static external IP address: $STATIC_IP_NAME..."
    gcloud compute addresses create $STATIC_IP_NAME --region ${ZONE%-*} --quiet
else
    print_status "Using existing static IP: $STATIC_IP_NAME"
fi

EXTERNAL_IP=$(gcloud compute addresses describe $STATIC_IP_NAME --region ${ZONE%-*} --format='value(address)')
print_status "External IP: $EXTERNAL_IP"

# 4. Create Firewall Rules (if not exists)
if ! gcloud compute firewall-rules describe allow-http-https &>/dev/null; then
    print_status "Creating firewall rules for port 80 and 443..."
    gcloud compute firewall-rules create allow-http-https \
        --description="Incoming http and https allowed" \
        --direction=INGRESS \
        --priority=1000 \
        --network=default \
        --action=ALLOW \
        --rules=tcp:80,tcp:443 \
        --source-ranges=0.0.0.0/0 \
        --quiet
fi

# 5. Create GCE Instance
if ! gcloud compute instances describe $INSTANCE_NAME --zone $ZONE &>/dev/null; then
    print_status "Creating GCE instance: $INSTANCE_NAME..."
    gcloud compute instances create $INSTANCE_NAME \
        --project=$PROJECT_ID \
        --zone=$ZONE \
        --machine-type=$MACHINE_TYPE \
        --network-interface=address=$EXTERNAL_IP,network-tier=PREMIUM \
        --maintenance-policy=MIGRATE \
        --provisioning-model=STANDARD \
        --scopes=https://www.googleapis.com/auth/cloud-platform \
        --tags=http-server,https-server \
        --create-disk=auto-delete=yes,boot=yes,device-name=$INSTANCE_NAME,image=projects/$IMAGE_PROJECT/global/images/family/$IMAGE_FAMILY,mode=rw,size=20,type=projects/$PROJECT_ID/zones/$ZONE/diskTypes/pd-balanced \
        --metadata-from-file=startup-script=gce-startup-production.sh \
        --quiet
else
    print_status "Instance $INSTANCE_NAME already exists. Skipping creation."
fi

# 6. Wait for VM and Startup Script
print_status "Waiting for VM to initialize (this can take 2-3 minutes)..."
# We wait a bit for the startup script to install Docker
sleep 30

# 7. Upload code and start container
print_status "Uploading code to VM..."
# Create a temporary archive to upload (excluding node_modules, venv, etc)
tar --exclude='venv' --exclude='__pycache__' --exclude='.git' -czf skillbridge-backend.tar.gz .

# Upload and extract
gcloud compute scp skillbridge-backend.tar.gz $INSTANCE_NAME:/tmp/ --zone $ZONE --quiet
gcloud compute ssh $INSTANCE_NAME --zone $ZONE --command "sudo mkdir -p /opt/skillbridge/backend && sudo tar -xzf /tmp/skillbridge-backend.tar.gz -C /opt/skillbridge/backend/ && sudo chown -R skillbridge:skillbridge /opt/skillbridge/backend" --quiet
rm skillbridge-backend.tar.gz

# Start the application
print_status "Starting the application with Docker Compose..."
gcloud compute ssh $INSTANCE_NAME --zone $ZONE --command "cd /opt/skillbridge/backend && sudo docker compose down && sudo docker compose up -d --build" --quiet

# 8. Final Verification
print_status "Checking health endpoint..."
max_retries=10
count=0
while [ $count -lt $max_retries ]; do
    if curl -s -f http://$EXTERNAL_IP/health > /dev/null; then
        print_success "Backend is UP and healthy at http://$EXTERNAL_IP"
        break
    fi
    print_status "Waiting for health check... ($((count+1))/$max_retries)"
    sleep 10
    count=$((count+1))
done

if [ $count -eq $max_retries ]; then
    print_warning "Health check timed out. Please check logs manually."
    echo "Command: gcloud compute ssh $INSTANCE_NAME --zone $ZONE --command \"sudo docker compose logs\""
fi

print_success "=========================================================="
print_success "   Deployment Complete!                                   "
print_success "   Static IP: $EXTERNAL_IP"
print_success "   Health: http://$EXTERNAL_IP/health"
print_success "=========================================================="
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Point your domain (e.g. api.skillbridge.tech) to $EXTERNAL_IP"
echo "2. SSH into the VM: gcloud compute ssh $INSTANCE_NAME --zone $ZONE"
echo "3. Run Certbot for SSL: sudo certbot --nginx -d yourdomain.com"
