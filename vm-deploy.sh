#!/bin/bash

# SkillBridge Backend - VM Deployment Script for Google Compute Engine
# Usage: ./vm-deploy.sh [create|deploy|update] [project-id] [instance-name]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ACTION=${1:-create}
PROJECT_ID=${2:-""}
INSTANCE_NAME=${3:-skillbridge-backend}
ZONE="us-central1-a"
MACHINE_TYPE="e2-standard-2"
BOOT_DISK_SIZE="20GB"
IMAGE_FAMILY="ubuntu-2004-lts"
IMAGE_PROJECT="ubuntu-os-cloud"

# Functions
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

check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if logged in to gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not logged in to gcloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

set_project() {
    if [ -z "$PROJECT_ID" ]; then
        print_info "Getting current project ID..."
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
        
        if [ -z "$PROJECT_ID" ]; then
            print_error "No project ID specified and no default project set."
            print_info "Usage: ./vm-deploy.sh [create|deploy|update] [project-id] [instance-name]"
            exit 1
        fi
    fi
    
    print_info "Using project: $PROJECT_ID"
    gcloud config set project $PROJECT_ID
}

enable_apis() {
    print_info "Enabling required APIs..."
    
    gcloud services enable \
        compute.googleapis.com \
        secretmanager.googleapis.com \
        iam.googleapis.com \
        --quiet
    
    print_success "APIs enabled"
}

create_firewall_rules() {
    print_info "Creating firewall rules..."
    
    # HTTP traffic
    if ! gcloud compute firewall-rules describe skillbridge-http &>/dev/null; then
        gcloud compute firewall-rules create skillbridge-http \
            --allow tcp:80 \
            --source-ranges 0.0.0.0/0 \
            --description "Allow HTTP traffic for SkillBridge"
    fi
    
    # HTTPS traffic
    if ! gcloud compute firewall-rules describe skillbridge-https &>/dev/null; then
        gcloud compute firewall-rules create skillbridge-https \
            --allow tcp:443 \
            --source-ranges 0.0.0.0/0 \
            --description "Allow HTTPS traffic for SkillBridge"
    fi
    
    # Backend service (for debugging)
    if ! gcloud compute firewall-rules describe skillbridge-backend &>/dev/null; then
        gcloud compute firewall-rules create skillbridge-backend \
            --allow tcp:8080 \
            --source-ranges 0.0.0.0/0 \
            --description "Allow backend service traffic for SkillBridge"
    fi
    
    print_success "Firewall rules created"
}

create_vm_instance() {
    print_info "Creating VM instance: $INSTANCE_NAME"
    
    # Check if instance already exists
    if gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE &>/dev/null; then
        print_warning "Instance $INSTANCE_NAME already exists"
        return 0
    fi
    
    # Create the instance
    gcloud compute instances create $INSTANCE_NAME \
        --zone=$ZONE \
        --machine-type=$MACHINE_TYPE \
        --network-interface=network-tier=PREMIUM,subnet=default \
        --maintenance-policy=MIGRATE \
        --provisioning-model=STANDARD \
        --service-account=default \
        --scopes=https://www.googleapis.com/auth/cloud-platform \
        --tags=http-server,https-server \
        --create-disk=auto-delete=yes,boot=yes,device-name=$INSTANCE_NAME,image=projects/$IMAGE_PROJECT/global/images/family/$IMAGE_FAMILY,mode=rw,size=$BOOT_DISK_SIZE,type=projects/$PROJECT_ID/zones/$ZONE/diskTypes/pd-standard \
        --no-shielded-secure-boot \
        --shielded-vtpm \
        --shielded-integrity-monitoring \
        --reservation-affinity=any
    
    print_success "VM instance created successfully"
    
    # Wait for instance to be ready
    print_info "Waiting for instance to be ready..."
    sleep 30
    
    # Get external IP
    EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)")
    print_success "Instance is ready! External IP: $EXTERNAL_IP"
}

setup_vm() {
    print_info "Setting up VM with required software..."
    
    # Copy setup script to VM
    gcloud compute scp vm-setup.sh $INSTANCE_NAME:~/vm-setup.sh --zone=$ZONE
    
    # Run setup script on VM
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="chmod +x ~/vm-setup.sh && sudo ~/vm-setup.sh"
    
    print_success "VM setup completed"
}

deploy_application() {
    print_info "Deploying application to VM..."
    
    # Create temporary deployment directory
    TEMP_DIR=$(mktemp -d)
    
    # Copy backend files to temporary directory
    cp -r . "$TEMP_DIR/backend"
    
    # Remove unnecessary files
    rm -rf "$TEMP_DIR/backend/.git" "$TEMP_DIR/backend/__pycache__" "$TEMP_DIR/backend/venv"
    
    # Copy files to VM
    gcloud compute scp --recurse "$TEMP_DIR/backend" $INSTANCE_NAME:/tmp/ --zone=$ZONE
    
    # Move files to correct location and set permissions
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
        sudo rm -rf /opt/skillbridge/backend/*
        sudo mv /tmp/backend/* /opt/skillbridge/backend/
        sudo chown -R skillbridge:skillbridge /opt/skillbridge/backend
        
        # Create .env file if it doesn't exist
        if [ ! -f /opt/skillbridge/backend/.env ]; then
            sudo -u skillbridge cp /opt/skillbridge/backend/.env.gcp /opt/skillbridge/backend/.env
        fi
        
        # Build and start the application
        cd /opt/skillbridge/backend
        sudo -u skillbridge docker-compose build --no-cache
        sudo systemctl restart skillbridge-backend
        
        # Wait for service to start
        sleep 30
        
        # Health check
        if curl -f http://localhost:8080/health > /dev/null 2>&1; then
            echo 'Application deployed successfully!'
        else
            echo 'Application deployment may have issues. Check logs.'
        fi
    "
    
    # Clean up temporary directory
    rm -rf "$TEMP_DIR"
    
    print_success "Application deployment completed"
}

update_application() {
    print_info "Updating application on VM..."
    
    # Run the deployment script on the VM
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
        sudo -u skillbridge /opt/skillbridge/deploy-app.sh
    "
    
    print_success "Application update completed"
}

show_instance_info() {
    print_info "Getting instance information..."
    
    EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)")
    INTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="get(networkInterfaces[0].networkIP)")
    STATUS=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="get(status)")
    
    print_success "Instance Information:"
    echo "  Name: $INSTANCE_NAME"
    echo "  Zone: $ZONE"
    echo "  Status: $STATUS"
    echo "  External IP: $EXTERNAL_IP"
    echo "  Internal IP: $INTERNAL_IP"
    echo ""
    echo "  Backend URL: http://$EXTERNAL_IP:8080"
    echo "  Health Check: http://$EXTERNAL_IP/health"
    echo ""
    echo "  SSH Command: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
    echo "  View Logs: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='docker-compose -f /opt/skillbridge/backend/docker-compose.yml logs'"
}

main() {
    print_info "Starting SkillBridge VM deployment..."
    print_info "Action: $ACTION"
    print_info "Instance: $INSTANCE_NAME"
    
    check_prerequisites
    set_project
    enable_apis
    create_firewall_rules
    
    case $ACTION in
        "create")
            create_vm_instance
            setup_vm
            deploy_application
            show_instance_info
            ;;
        "deploy")
            deploy_application
            show_instance_info
            ;;
        "update")
            update_application
            show_instance_info
            ;;
        "info")
            show_instance_info
            ;;
        *)
            print_error "Invalid action. Use 'create', 'deploy', 'update', or 'info'"
            exit 1
            ;;
    esac
    
    print_success "VM deployment completed successfully!"
    print_info ""
    print_info "Next steps:"
    print_info "1. Update environment variables: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
    print_info "2. Edit /opt/skillbridge/backend/.env with your actual values"
    print_info "3. Restart service: sudo systemctl restart skillbridge-backend"
    print_info "4. Set up SSL certificate: sudo certbot --nginx -d your-domain.com"
    print_info "5. Configure DNS to point to External IP: $EXTERNAL_IP"
}

# Show usage if no arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 [create|deploy|update|info] [project-id] [instance-name]"
    echo ""
    echo "Actions:"
    echo "  create  - Create new VM instance and deploy application"
    echo "  deploy  - Deploy application to existing VM"
    echo "  update  - Update application on existing VM"
    echo "  info    - Show instance information"
    echo ""
    echo "Examples:"
    echo "  $0 create my-project-id skillbridge-prod"
    echo "  $0 deploy my-project-id skillbridge-prod"
    echo "  $0 update my-project-id skillbridge-prod"
    echo "  $0 info my-project-id skillbridge-prod"
    exit 1
fi

# Run main function
main