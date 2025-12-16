#!/bin/bash

# TrueLift AI - GCP Cloud Run Deployment Script
# Deploys all services with min=0 instances for cost optimization

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
REGION=${GCP_REGION:-"us-central1"}
REGISTRY="gcr.io/${PROJECT_ID}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}TrueLift AI - Cloud Run Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${YELLOW}Error: gcloud CLI not found. Please install it first.${NC}"
    exit 1
fi

# Set project
echo -e "${GREEN}Setting GCP project: ${PROJECT_ID}${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${GREEN}Enabling required GCP APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    containerregistry.googleapis.com \
    cloudbuild.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    secretmanager.googleapis.com

# Build and push Docker images
echo -e "${GREEN}Building and pushing Docker images...${NC}"

# Backend API
echo -e "${BLUE}Building backend-api...${NC}"
gcloud builds submit ./backend \
    --tag ${REGISTRY}/backend-api:latest \
    --timeout=10m

# Frontend
echo -e "${BLUE}Building frontend...${NC}"
gcloud builds submit ./frontend \
    --tag ${REGISTRY}/frontend:latest \
    --timeout=10m

# ML Detector
echo -e "${BLUE}Building ml-detector...${NC}"
gcloud builds submit ./services/ml-detector \
    --tag ${REGISTRY}/ml-detector:latest \
    --timeout=10m

# Gemini Agent
echo -e "${BLUE}Building gemini-agent...${NC}"
gcloud builds submit ./services/gemini-agent \
    --tag ${REGISTRY}/gemini-agent:latest \
    --timeout=10m

# Feedback Loop
echo -e "${BLUE}Building feedback-loop...${NC}"
gcloud builds submit ./services/feedback-loop \
    --tag ${REGISTRY}/feedback-loop:latest \
    --timeout=10m

# Virtual Shoppers
echo -e "${BLUE}Building virtual-shoppers...${NC}"
gcloud builds submit ./services/virtual-shoppers \
    --tag ${REGISTRY}/virtual-shoppers:latest \
    --timeout=10m

# Deploy services to Cloud Run
echo -e "${GREEN}Deploying services to Cloud Run...${NC}"

# Backend API - Public facing, higher capacity
echo -e "${BLUE}Deploying backend-api...${NC}"
gcloud run deploy backend-api \
    --image ${REGISTRY}/backend-api:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 10 \
    --memory 1Gi \
    --cpu 2 \
    --timeout 300 \
    --set-env-vars="KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092},POSTGRES_HOST=${POSTGRES_HOST:-postgres},POSTGRES_DB=truelift,POSTGRES_USER=truelift_user,POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-truelift_pass},REDIS_HOST=${REDIS_HOST:-redis},REDIS_PORT=6379,GEMINI_API_KEY=${GEMINI_API_KEY}"

# Frontend - Public facing
echo -e "${BLUE}Deploying frontend...${NC}"
gcloud run deploy frontend \
    --image ${REGISTRY}/frontend:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 5 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 60 \
    --set-env-vars="NEXT_PUBLIC_API_URL=https://backend-api-${PROJECT_ID}.${REGION}.run.app"

# ML Detector - Internal service
echo -e "${BLUE}Deploying ml-detector...${NC}"
gcloud run deploy ml-detector \
    --image ${REGISTRY}/ml-detector:latest \
    --platform managed \
    --region ${REGION} \
    --no-allow-unauthenticated \
    --min-instances 0 \
    --max-instances 3 \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --set-env-vars="KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS},POSTGRES_HOST=${POSTGRES_HOST},POSTGRES_DB=truelift,POSTGRES_USER=truelift_user,POSTGRES_PASSWORD=${POSTGRES_PASSWORD},REDIS_HOST=${REDIS_HOST},REDIS_PORT=6379"

# Gemini Agent - Internal service
echo -e "${BLUE}Deploying gemini-agent...${NC}"
gcloud run deploy gemini-agent \
    --image ${REGISTRY}/gemini-agent:latest \
    --platform managed \
    --region ${REGION} \
    --no-allow-unauthenticated \
    --min-instances 0 \
    --max-instances 3 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --set-env-vars="KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS},POSTGRES_HOST=${POSTGRES_HOST},POSTGRES_DB=truelift,POSTGRES_USER=truelift_user,POSTGRES_PASSWORD=${POSTGRES_PASSWORD},GEMINI_API_KEY=${GEMINI_API_KEY}"

# Feedback Loop - Internal service
echo -e "${BLUE}Deploying feedback-loop...${NC}"
gcloud run deploy feedback-loop \
    --image ${REGISTRY}/feedback-loop:latest \
    --platform managed \
    --region ${REGION} \
    --no-allow-unauthenticated \
    --min-instances 0 \
    --max-instances 3 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --set-env-vars="KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS},POSTGRES_HOST=${POSTGRES_HOST},POSTGRES_DB=truelift,POSTGRES_USER=truelift_user,POSTGRES_PASSWORD=${POSTGRES_PASSWORD},REDIS_HOST=${REDIS_HOST},REDIS_PORT=6379"

# Virtual Shoppers - Internal service (optional, can be paused)
echo -e "${BLUE}Deploying virtual-shoppers...${NC}"
gcloud run deploy virtual-shoppers \
    --image ${REGISTRY}/virtual-shoppers:latest \
    --platform managed \
    --region ${REGION} \
    --no-allow-unauthenticated \
    --min-instances 0 \
    --max-instances 2 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --set-env-vars="KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS},REDIS_HOST=${REDIS_HOST},REDIS_PORT=6379,SIMULATION_ENABLED=${SIMULATION_ENABLED:-true}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Frontend URL:${NC}"
gcloud run services describe frontend --region ${REGION} --format='value(status.url)'
echo ""
echo -e "${BLUE}Backend API URL:${NC}"
gcloud run services describe backend-api --region ${REGION} --format='value(status.url)'
echo ""
echo -e "${YELLOW}Note: Services are configured with min-instances=0 for cost optimization.${NC}"
echo -e "${YELLOW}First request may take 10-30 seconds (cold start).${NC}"
echo ""
echo -e "${YELLOW}To pause virtual shoppers and reduce costs:${NC}"
echo -e "  gcloud run services update virtual-shoppers --region ${REGION} --set-env-vars='SIMULATION_ENABLED=false'"
