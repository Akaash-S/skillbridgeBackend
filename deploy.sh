#!/bin/bash

# SkillBridge Backend Deployment Script for Google Cloud Platform
# Usage: ./deploy.sh [cloud-run|app-engine] [project-id]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEPLOYMENT_TYPE=${1:-cloud-run}
PROJECT_ID=${2:-""}
REGION="us-central1"
SERVICE_NAME="skillbridge-backend"

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
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install it first."
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
            print_info "Usage: ./deploy.sh [cloud-run|app-engine] [project-id]"
            exit 1
        fi
    fi
    
    print_info "Using project: $PROJECT_ID"
    gcloud config set project $PROJECT_ID
}

enable_apis() {
    print_info "Enabling required APIs..."
    
    gcloud services enable \
        cloudbuild.googleapis.com \
        run.googleapis.com \
        containerregistry.googleapis.com \
        secretmanager.googleapis.com \
        iam.googleapis.com \
        --quiet
    
    print_success "APIs enabled"
}

create_secrets() {
    print_info "Creating secrets in Secret Manager..."
    
    # List of required secrets
    secrets=(
        "skillbridge-secret-key"
        "gemini-api-key"
        "adzuna-app-id"
        "adzuna-app-key"
        "smtp-host"
        "smtp-port"
        "smtp-user"
        "smtp-password"
    )
    
    for secret in "${secrets[@]}"; do
        if ! gcloud secrets describe $secret &>/dev/null; then
            print_warning "Secret $secret does not exist. Creating placeholder..."
            echo "REPLACE_WITH_ACTUAL_VALUE" | gcloud secrets create $secret --data-file=-
            print_warning "Please update secret $secret with actual value using:"
            print_warning "echo 'actual_value' | gcloud secrets versions add $secret --data-file=-"
        else
            print_info "Secret $secret already exists"
        fi
    done
}

create_service_account() {
    print_info "Creating service account..."
    
    SA_NAME="skillbridge-backend"
    SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
    
    if ! gcloud iam service-accounts describe $SA_EMAIL &>/dev/null; then
        gcloud iam service-accounts create $SA_NAME \
            --display-name="SkillBridge Backend Service Account" \
            --description="Service account for SkillBridge backend application"
        
        # Grant necessary roles
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:$SA_EMAIL" \
            --role="roles/secretmanager.secretAccessor"
        
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:$SA_EMAIL" \
            --role="roles/firebase.admin"
        
        print_success "Service account created and configured"
    else
        print_info "Service account already exists"
    fi
}

deploy_cloud_run() {
    print_info "Deploying to Cloud Run..."
    
    # Build and deploy using Cloud Build
    gcloud builds submit --config=cloudbuild.yaml ..
    
    print_success "Deployment to Cloud Run completed!"
    
    # Get the service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
    print_success "Service URL: $SERVICE_URL"
}

deploy_app_engine() {
    print_info "Deploying to App Engine..."
    
    # Check if App Engine app exists
    if ! gcloud app describe &>/dev/null; then
        print_info "Creating App Engine application..."
        gcloud app create --region=$REGION
    fi
    
    # Deploy to App Engine
    gcloud app deploy app.yaml --quiet
    
    print_success "Deployment to App Engine completed!"
    
    # Get the service URL
    SERVICE_URL=$(gcloud app describe --format="value(defaultHostname)")
    print_success "Service URL: https://$SERVICE_URL"
}

main() {
    print_info "Starting SkillBridge Backend deployment..."
    print_info "Deployment type: $DEPLOYMENT_TYPE"
    
    check_prerequisites
    set_project
    enable_apis
    create_secrets
    create_service_account
    
    case $DEPLOYMENT_TYPE in
        "cloud-run")
            deploy_cloud_run
            ;;
        "app-engine")
            deploy_app_engine
            ;;
        *)
            print_error "Invalid deployment type. Use 'cloud-run' or 'app-engine'"
            exit 1
            ;;
    esac
    
    print_success "Deployment completed successfully!"
    print_info "Don't forget to:"
    print_info "1. Update secrets with actual values"
    print_info "2. Configure your frontend to use the new backend URL"
    print_info "3. Set up custom domain if needed"
    print_info "4. Configure monitoring and logging"
}

# Run main function
main