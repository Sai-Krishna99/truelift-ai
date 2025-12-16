# TrueLift AI - GCP Infrastructure Setup Guide

## Prerequisites

1. **GCP Project**: Create or select a GCP project
2. **gcloud CLI**: Install and authenticate
3. **APIs**: Enable required APIs (automated in deploy script)
4. **Confluent Cloud**: Sign up for Confluent Cloud Kafka (free tier available)
5. **Secrets**: Set up secrets in Secret Manager

## Quick Start

```bash
# 1. Set environment variables
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export POSTGRES_PASSWORD="your-secure-password"
export GEMINI_API_KEY="your-gemini-api-key"
export KAFKA_BOOTSTRAP_SERVERS="your-confluent-kafka-bootstrap.confluent.cloud:9092"
export KAFKA_API_KEY="your-kafka-api-key"
export KAFKA_API_SECRET="your-kafka-secret"

# 2. Create Cloud SQL instance (PostgreSQL)
gcloud sql instances create truelift-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=${GCP_REGION} \
    --no-backup

# Create database
gcloud sql databases create truelift --instance=truelift-db

# Create user
gcloud sql users create truelift_user \
    --instance=truelift-db \
    --password=${POSTGRES_PASSWORD}

# 3. Create Cloud Memorystore (Redis) instance
gcloud redis instances create truelift-redis \
    --size=1 \
    --region=${GCP_REGION} \
    --redis-version=redis_7_0 \
    --tier=basic

# 4. Get connection details
export POSTGRES_HOST=$(gcloud sql instances describe truelift-db --format='value(connectionName)')
export REDIS_HOST=$(gcloud redis instances describe truelift-redis --region=${GCP_REGION} --format='value(host)')

# 5. Run deployment
chmod +x deploy-cloudrun.sh
./deploy-cloudrun.sh
```

## Cost Optimization

### 1. Cloud Run Configuration
- **min-instances=0**: Scale to zero when idle (FREE tier eligible)
- **max-instances**: Capped to prevent runaway costs
  - backend-api: 10 instances (2 vCPU, 1GB each)
  - frontend: 5 instances (1 vCPU, 512MB each)
  - ml-detector: 3 instances (1 vCPU, 1GB each)
  - gemini-agent: 3 instances (1 vCPU, 512MB each)
  - feedback-loop: 3 instances (1 vCPU, 512MB each)
  - virtual-shoppers: 2 instances (1 vCPU, 512MB each)

### 2. Confluent Cloud Kafka
- Use **Basic cluster** ($0/mo for 30-day trial, then ~$5-10/mo)
- **Retention**: Set to 24 hours to reduce storage costs
- **Partitions**: Single partition per topic for demo
- **Pause simulation**: Stop virtual-shoppers to halt event generation

### 3. Cloud SQL (PostgreSQL)
- **Tier**: db-f1-micro (1 vCPU, 0.6GB RAM) ~$7/mo
- **Backups**: Disabled for dev (enable for prod)
- **Connection pooling**: Use PgBouncer or built-in pooling

### 4. Cloud Memorystore (Redis)
- **Tier**: Basic (no replication) ~$37/mo for 1GB
- **Alternative**: Use Redis Labs free tier or in-memory for dev

## Kafka Cost Controls

### Pause Virtual Shoppers
```bash
# Stop event generation
gcloud run services update virtual-shoppers \
    --region ${GCP_REGION} \
    --set-env-vars='SIMULATION_ENABLED=false'

# Resume event generation
gcloud run services update virtual-shoppers \
    --region ${GCP_REGION} \
    --set-env-vars='SIMULATION_ENABLED=true'
```

### Confluent Cloud Topic Configuration
```bash
# Reduce retention to 1 hour (3600000 ms)
confluent kafka topic update shopping-events \
    --config retention.ms=3600000

confluent kafka topic update cannibalization-alerts \
    --config retention.ms=3600000

confluent kafka topic update user-actions \
    --config retention.ms=3600000
```

### Scale Topics
```bash
# Reduce partitions to 1 (lower cost)
confluent kafka topic update shopping-events --partitions 1
```

## Environment-Based Configuration

### Development (Local)
- PostgreSQL: Docker container
- Redis: Docker container
- Kafka: Docker container (Confluent CP)
- All services: Docker Compose

### Production (GCP)
- PostgreSQL: Cloud SQL (db-f1-micro)
- Redis: Cloud Memorystore (Basic, 1GB)
- Kafka: Confluent Cloud (Basic cluster)
- All services: Cloud Run (min=0 instances)

## Monitoring & Alerts

### Set up billing alerts
```bash
# Create budget alert at $50/month
gcloud billing budgets create \
    --billing-account=YOUR_BILLING_ACCOUNT_ID \
    --display-name="TrueLift Budget Alert" \
    --budget-amount=50USD \
    --threshold-rule=percent=50 \
    --threshold-rule=percent=90 \
    --threshold-rule=percent=100
```

### Monitor Cloud Run costs
```bash
# Check current costs
gcloud run services list --region=${GCP_REGION}

# Get metrics
gcloud monitoring time-series list \
    --filter='metric.type="run.googleapis.com/request_count"'
```

## Scaling Strategy

### Cold Start Optimization
- **Minimum instances**: Keep at 0 for cost (accept cold starts)
- **Warm instances**: Set min=1 for critical services if needed (costs more)
- **Cold start time**: 10-30 seconds for first request

### Auto-Scaling Rules
- **CPU threshold**: 80% utilization triggers scale-up
- **Concurrency**: 80 concurrent requests per instance
- **Scale-down**: 5-minute idle timeout before scale-to-zero

## Database Connection Pooling

### Using Cloud SQL Proxy
```bash
# Install Cloud SQL Proxy
cloud-sql-proxy your-project:us-central1:truelift-db --port 5432
```

### Connection String Format
```
postgresql://truelift_user:PASSWORD@/truelift?host=/cloudsql/PROJECT:REGION:INSTANCE
```

## Secrets Management

```bash
# Store Gemini API Key
echo -n "your-gemini-api-key" | gcloud secrets create gemini-api-key --data-file=-

# Store Kafka credentials
echo -n "your-kafka-secret" | gcloud secrets create kafka-api-secret --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## Troubleshooting

### Service not scaling
- Check logs: `gcloud run services logs read SERVICE_NAME --region=${GCP_REGION}`
- Verify env vars: `gcloud run services describe SERVICE_NAME --region=${GCP_REGION}`

### Database connection issues
- Use Cloud SQL Proxy for local testing
- Enable Cloud SQL Admin API
- Check firewall rules

### Kafka connection issues
- Verify Confluent Cloud credentials
- Check network connectivity
- Ensure API key has correct permissions

## Estimated Monthly Costs

### Minimal Usage (Development)
- Cloud Run: $0 (within free tier, min-instances=0)
- Cloud SQL: $7 (db-f1-micro)
- Cloud Memorystore: $37 (Basic 1GB)
- Confluent Cloud: $0-10 (Basic cluster)
- **Total: ~$44-54/month**

### Moderate Usage (Production)
- Cloud Run: $20-40 (actual usage-based)
- Cloud SQL: $20 (db-g1-small with backups)
- Cloud Memorystore: $37-75 (Basic/Standard tier)
- Confluent Cloud: $10-20 (Basic cluster)
- **Total: ~$87-155/month**

### To Minimize Costs
1. ✅ Use min-instances=0 (free when idle)
2. ✅ Pause virtual-shoppers when not demoing
3. ✅ Set Kafka retention to 1 hour
4. ✅ Use db-f1-micro for Cloud SQL
5. ✅ Disable backups in dev
6. ✅ Set billing alerts
7. ✅ Delete unused resources regularly
