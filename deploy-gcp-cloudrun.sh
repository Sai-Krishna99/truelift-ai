#!/bin/bash

# TrueLift AI - GCP Cloud Run Deployment Script
# This script deploys all services to Google Cloud Run with cost optimization (min instances = 0)

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-truelift-ai}"
REGION="${GCP_REGION:-us-east1}"
SQL_INSTANCE="truelift-ai:us-east1:truelift-db"

echo "🚀 Deploying TrueLift AI to GCP Cloud Run"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "SQL Instance: $SQL_INSTANCE"

# Ensure we're using the correct project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "📦 Enabling required GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com

# Get Project Number for IAM
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

# Grant permissions to service account
echo "🔑 Granting Secret Manager & Cloud SQL permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None > /dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudsql.client" \
  --condition=None > /dev/null

# Create secrets for sensitive data
echo "🔐 Creating secrets..."
if ! gcloud secrets describe gemini-api-key --project=$PROJECT_ID &>/dev/null; then
  echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
    --data-file=- \
    --replication-policy="automatic"
fi

if ! gcloud secrets describe postgres-password --project=$PROJECT_ID &>/dev/null; then
  echo -n "$POSTGRES_PASSWORD" | gcloud secrets create postgres-password \
    --data-file=- \
    --replication-policy="automatic"
fi

# Kafka Secrets
if [ -n "$KAFKA_SASL_USERNAME" ]; then
    if ! gcloud secrets describe kafka-sasl-username --project=$PROJECT_ID &>/dev/null; then
      echo -n "$KAFKA_SASL_USERNAME" | gcloud secrets create kafka-sasl-username --data-file=- --replication-policy="automatic"
    fi
    if ! gcloud secrets describe kafka-sasl-password --project=$PROJECT_ID &>/dev/null; then
      echo -n "$KAFKA_SASL_PASSWORD" | gcloud secrets create kafka-sasl-password --data-file=- --replication-policy="automatic"
    fi
    KAFKA_SECRETS_ARGS="--set-secrets=KAFKA_SASL_USERNAME=kafka-sasl-username:latest,KAFKA_SASL_PASSWORD=kafka-sasl-password:latest"
    KAFKA_ENV_ARGS="KAFKA_SECURITY_PROTOCOL=${KAFKA_SECURITY_PROTOCOL:-SASL_SSL}"
else
    echo "⚠️  No Kafka credentials provided (KAFKA_SASL_USERNAME). Assuming plaintext/local or previously set secrets."
    KAFKA_SECRETS_ARGS=""
    KAFKA_ENV_ARGS="KAFKA_SECURITY_PROTOCOL=PLAINTEXT"
fi

# PostgreSQL connection string for internal VPC/Proxy
DB_HOST="/cloudsql/${SQL_INSTANCE}"

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
  --set-env-vars="POSTGRES_HOST=${DB_HOST},POSTGRES_DB=${POSTGRES_DB},POSTGRES_USER=${POSTGRES_USER},REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS},${KAFKA_ENV_ARGS}" \
  --set-secrets="POSTGRES_PASSWORD=postgres-password:latest" \
  --vpc-connector=truelift-connector \
  --add-cloudsql-instances=$SQL_INSTANCE \
  ${KAFKA_SECRETS_ARGS}

# Get backend URL
BACKEND_URL=$(gcloud run services describe truelift-backend --region=$REGION --format='value(status.url)')
echo "✅ Backend deployed at: $BACKEND_URL"

# Deploy Frontend
echo "🎨 Deploying Frontend..."
# The "Clean" engineering way: Generate a temporary .env.production 
# so Next.js picks up the variable during build.
cat <<EOF > frontend/.env.production
NEXT_PUBLIC_API_URL=${BACKEND_URL}
EOF

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

# Cleanup
rm frontend/.env.production


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
  --set-env-vars="POSTGRES_HOST=${DB_HOST},POSTGRES_DB=${POSTGRES_DB},POSTGRES_USER=${POSTGRES_USER},REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS},BACKEND_URL=${BACKEND_URL},${KAFKA_ENV_ARGS}" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,POSTGRES_PASSWORD=postgres-password:latest" \
  --vpc-connector=truelift-connector \
  --add-cloudsql-instances=$SQL_INSTANCE \
  ${KAFKA_SECRETS_ARGS}

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
  --set-env-vars="POSTGRES_HOST=${DB_HOST},POSTGRES_DB=${POSTGRES_DB},POSTGRES_USER=${POSTGRES_USER},REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS},${KAFKA_ENV_ARGS}" \
  --set-secrets="POSTGRES_PASSWORD=postgres-password:latest" \
  --vpc-connector=truelift-connector \
  --add-cloudsql-instances=$SQL_INSTANCE \
  ${KAFKA_SECRETS_ARGS}

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
  --set-env-vars="POSTGRES_HOST=${DB_HOST},POSTGRES_DB=${POSTGRES_DB},POSTGRES_USER=${POSTGRES_USER},REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS},${KAFKA_ENV_ARGS}" \
  --set-secrets="POSTGRES_PASSWORD=postgres-password:latest" \
  --vpc-connector=truelift-connector \
  --add-cloudsql-instances=$SQL_INSTANCE \
  ${KAFKA_SECRETS_ARGS}


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
  --set-env-vars="REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS},DEMO_MODE=true,${KAFKA_ENV_ARGS}" \
  --vpc-connector=truelift-connector \
  ${KAFKA_SECRETS_ARGS}

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
