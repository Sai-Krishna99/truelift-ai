#!/bin/bash

# TrueLift AI - GCP Cloud Run Deployment Script
# This script deploys all services to Google Cloud Run with cost optimization (min instances = 0)

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-truelift-ai}"
REGION="${GCP_REGION:-us-central1}"

echo "🚀 Deploying TrueLift AI to GCP Cloud Run"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Ensure we're using the correct project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "📦 Enabling required GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  sql-component.googleapis.com \
  redis.googleapis.com

# Create secrets for sensitive data
echo "🔐 Creating secrets..."
if ! gcloud secrets describe gemini-api-key --project=$PROJECT_ID &>/dev/null; then
  echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
    --data-file=- \
    --replication-policy="automatic"
fi

# Deploy Backend API
echo "🔧 Deploying Backend API..."
gcloud run deploy truelift-backend \
  --source=./backend \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=5 \
  --cpu=1 \
  --memory=512Mi \
  --concurrency=80 \
  --timeout=300 \
  --set-env-vars="POSTGRES_HOST=${POSTGRES_HOST},POSTGRES_DB=${POSTGRES_DB},POSTGRES_USER=${POSTGRES_USER},REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}" \
  --set-secrets="POSTGRES_PASSWORD=postgres-password:latest"

# Get backend URL
BACKEND_URL=$(gcloud run services describe truelift-backend --region=$REGION --format='value(status.url)')
echo "✅ Backend deployed at: $BACKEND_URL"

# Deploy Frontend
echo "🎨 Deploying Frontend..."
gcloud run deploy truelift-frontend \
  --source=./frontend \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=3 \
  --cpu=1 \
  --memory=512Mi \
  --timeout=60 \
  --set-env-vars="NEXT_PUBLIC_API_URL=${BACKEND_URL}"

FRONTEND_URL=$(gcloud run services describe truelift-frontend --region=$REGION --format='value(status.url)')
echo "✅ Frontend deployed at: $FRONTEND_URL"

# Deploy Gemini Agent
echo "🤖 Deploying Gemini Agent..."
gcloud run deploy truelift-gemini-agent \
  --source=./services/gemini-agent \
  --region=$REGION \
  --platform=managed \
  --no-allow-unauthenticated \
  --min-instances=0 \
  --max-instances=2 \
  --cpu=1 \
  --memory=512Mi \
  --timeout=300 \
  --set-env-vars="POSTGRES_HOST=${POSTGRES_HOST},POSTGRES_DB=${POSTGRES_DB},POSTGRES_USER=${POSTGRES_USER},REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS},BACKEND_URL=${BACKEND_URL}" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,POSTGRES_PASSWORD=postgres-password:latest"

echo "✅ Gemini Agent deployed"

# Deploy ML Detector
echo "🔍 Deploying ML Detector..."
gcloud run deploy truelift-ml-detector \
  --source=./services/ml-detector \
  --region=$REGION \
  --platform=managed \
  --no-allow-unauthenticated \
  --min-instances=0 \
  --max-instances=2 \
  --cpu=2 \
  --memory=1Gi \
  --timeout=300 \
  --set-env-vars="POSTGRES_HOST=${POSTGRES_HOST},POSTGRES_DB=${POSTGRES_DB},POSTGRES_USER=${POSTGRES_USER},REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}" \
  --set-secrets="POSTGRES_PASSWORD=postgres-password:latest"

echo "✅ ML Detector deployed"

# Deploy Feedback Loop
echo "🔄 Deploying Feedback Loop..."
gcloud run deploy truelift-feedback-loop \
  --source=./services/feedback-loop \
  --region=$REGION \
  --platform=managed \
  --no-allow-unauthenticated \
  --min-instances=0 \
  --max-instances=2 \
  --cpu=1 \
  --memory=512Mi \
  --timeout=300 \
  --set-env-vars="POSTGRES_HOST=${POSTGRES_HOST},POSTGRES_DB=${POSTGRES_DB},POSTGRES_USER=${POSTGRES_USER},REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}" \
  --set-secrets="POSTGRES_PASSWORD=postgres-password:latest"

echo "✅ Feedback Loop deployed"

# Deploy Virtual Shoppers (optional - for demo mode)
echo "🛍️  Deploying Virtual Shoppers..."
gcloud run deploy truelift-virtual-shoppers \
  --source=./services/virtual-shoppers \
  --region=$REGION \
  --platform=managed \
  --no-allow-unauthenticated \
  --min-instances=0 \
  --max-instances=1 \
  --cpu=1 \
  --memory=512Mi \
  --timeout=300 \
  --set-env-vars="REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS},DEMO_MODE=true"

echo "✅ Virtual Shoppers deployed"

echo ""
echo "🎉 Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Frontend URL: $FRONTEND_URL"
echo "Backend URL:  $BACKEND_URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  Cost Optimization Notes:"
echo "  • All services have min instances = 0 (cold starts expected)"
echo "  • First request after idle may take 5-15 seconds"
echo "  • Max instances configured to prevent runaway costs"
echo ""
echo "📊 Monitor costs at: https://console.cloud.google.com/billing"
