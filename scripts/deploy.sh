#!/bin/bash
# SkillBridge Consolidated Deployment Script
# Usage:
#   ./scripts/deploy.sh [compose | cloud-run | app-engine] [project-id]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

DEPLOY_TARGET=${1:-compose}
PROJECT_ID=${2:-""}

echo "🚀 SkillBridge Deployment Manager"
echo "Target: $DEPLOY_TARGET"

case "$DEPLOY_TARGET" in
    compose)
        echo "🐳 Starting Docker Compose production deployment..."
        if [ ! -f ".env" ]; then
            echo "❌ Error: .env file missing in $ROOT_DIR. Please copy .env.example."
            exit 1
        fi

        mkdir -p logs/nginx logs/app nginx/ssl redis
        if [ ! -f "nginx/ssl/fullchain.pem" ]; then
            echo "⚠️  SSL certificate missing. Generating self-signed cert for now..."
            ./scripts/setup-ssl.sh self-signed
        fi

        echo "🏗️  Building and bringing up services..."
        docker-compose -f docker-compose.prod.yml down --remove-orphans
        docker-compose -f docker-compose.prod.yml build --no-cache
        docker-compose -f docker-compose.prod.yml up -d

        echo "⏳ Waiting 10s for container startup..."
        sleep 10

        echo "🏥 Health check:"
        if curl -f -s http://localhost/health > /dev/null 2>&1 || curl -k -f -s https://localhost/health > /dev/null 2>&1; then
            echo "✅ SkillBridge backend is healthy and responding!"
        else
            echo "⚠️  Service container up but health check pending or failed. Checking logs:"
            docker-compose -f docker-compose.prod.yml logs --tail=25
        fi
        ;;

    cloud-run|app-engine)
        echo "☁️  Dispatching to GCP Deployment ($DEPLOY_TARGET)..."
        ./deploy.sh "$DEPLOY_TARGET" "$PROJECT_ID"
        ;;

    *)
        echo "❌ Unknown deployment target: $DEPLOY_TARGET"
        echo "Usage: ./scripts/deploy.sh [compose | cloud-run | app-engine] [project-id]"
        exit 1
        ;;
esac
