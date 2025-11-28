#!/bin/bash

set -e

echo "🚀 Deploying TrueLift AI to Google Cloud Platform..."

GCP_PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
GCP_REGION=${GCP_REGION:-"us-central1"}
GCS_BUCKET=${GCS_BUCKET:-"truelift-ml-models"}

echo "📋 Project: $GCP_PROJECT_ID"
echo "📍 Region: $GCP_REGION"

gcloud config set project $GCP_PROJECT_ID

echo "1️⃣ Creating GCS bucket for ML models..."
gsutil mb -p $GCP_PROJECT_ID -c STANDARD -l $GCP_REGION gs://$GCS_BUCKET/ || echo "Bucket already exists"

echo "2️⃣ Creating BigQuery dataset..."
bq mk --dataset --location=$GCP_REGION $GCP_PROJECT_ID:truelift_data || echo "Dataset already exists"

echo "3️⃣ Building and deploying Inference Service to Cloud Run..."
cd ml-models
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/inference-service -f Dockerfile.inference .

gcloud run deploy inference-service \
  --image gcr.io/$GCP_PROJECT_ID/inference-service \
  --platform managed \
  --region $GCP_REGION \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=$GCP_PROJECT_ID,GCP_REGION=$GCP_REGION" \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10

cd ..

echo "4️⃣ Setting up Cloud SQL for Product Catalog..."
gcloud sql instances create truelift-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$GCP_REGION \
  --root-password=change_this_password || echo "Instance already exists"

gcloud sql databases create truelift --instance=truelift-postgres || echo "Database already exists"

echo "5️⃣ Enabling required APIs..."
gcloud services enable \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  cloudbuild.googleapis.com \
  cloudrun.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com

echo "6️⃣ Creating Confluent Cloud Kafka cluster..."
echo "⚠️  Please create Confluent Cloud cluster manually and update .env with credentials"
echo "   Visit: https://confluent.cloud/"

echo ""
echo "✅ GCP Infrastructure deployed!"
echo ""
echo "Next steps:"
echo "1. Train Vertex AI model: python ml-models/vertex_ai_integration.py"
echo "2. Deploy model endpoint"
echo "3. Update .env with endpoint ID"
echo "4. Set up Confluent Cloud and update Kafka credentials"
echo "5. Deploy application services"
