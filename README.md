# TrueLift AI - Real-Time Promotional Cannibalization Detection

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Detect promotional cannibalization in real-time and respond with AI-powered strategies.**

## Quick Highlights

- **Real-Time Detection**: ML models identify cannibalization within 1-minute windows
- **AI-Powered Insights**: Gemini Pro explains causes and recommends strategies
- **Automated Response**: Dynamic pricing and promotion adjustments
- **Continuous Learning**: Feedback loop improves accuracy over time
- **Production Ready**: Deployed on GCP Cloud Run with Confluent Kafka

## High Level Workflow

<img width="2628" height="1062" alt="workflow" src="https://github.com/user-attachments/assets/51a41595-c688-44d3-b599-4cb8c302b2f5" />
<img width="438" height="1181" alt="image" src="https://github.com/user-attachments/assets/0fd942ed-538a-4714-afa9-259b72e96c80" />

## Architecture and Technical Overview

<img width="1626" height="4062" alt="architecture" src="https://github.com/user-attachments/assets/4a466576-ed41-4880-aa94-e3940e34f325" />
<img width="798" height="1307" alt="image" src="https://github.com/user-attachments/assets/8b8cb652-a912-4aa6-9dae-85a6ff9d51fd" />

## The Problem

When retailers run promotions:
- Promoted products steal sales from regular-priced items
- Margin erosion without incremental revenue
- Difficult to detect in real-time
- Manual analysis takes days or weeks
- No automated response mechanism
- Lost revenue and wasted marketing spend

## The Solution

TrueLift AI provides:
- **Real-time detection** with 1-minute aggregation windows
- **ML-powered predictions** comparing actual vs expected sales
- **AI explanations** via Gemini Pro for human-readable insights
- **Automated actions** like stopping promotions or adjusting prices
- **Feedback loop** that measures effectiveness and improves over time
- **Live dashboard** with WebSocket updates

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14 + React 18 | Real-time dashboard with TypeScript |
| **Backend** | FastAPI + Python 3.11 | REST API and WebSocket server |
| **ML/AI** | Vertex AI + Gemini Pro | Cannibalization detection and AI reasoning |
| **Streaming** | Confluent Cloud Kafka | Real-time event streaming |
| **Processing** | Apache Flink | Stream aggregations |
| **Database** | Cloud SQL (PostgreSQL) | Product catalog and operational data |
| **Cache** | Redis | Fast data access |
| **Deployment** | GCP Cloud Run | Serverless microservices |

## System Components

### Phase 1: Vertex AI Training
- **BigQuery**: Historical sales data storage and analytics
- **Vertex AI AutoML**: Automated model training (Tabular Regression)
- **Vertex AI Model Registry**: Model versioning (XGBoost/LightGBM)
- **GCS**: Training data and model artifact storage

### Phase 2: Real-Time Detection Pipeline
- **Shopper Simulator**: Generates live shopping events
- **Confluent Cloud**: Kafka streaming platform
- **Flink SQL**: 1-minute windowed aggregations
- **Inference Service (Cloud Run)**: Real-time predictions
- **ML Detector**: Compares actual vs predicted sales
- **Gemini Pro**: AI-powered loss explanation and strategy generation

### Phase 3: Frontend & Action
- **TrueLift Dashboard**: Next.js real-time UI
- **Backend API**: FastAPI REST service
- **Cloud SQL**: Product catalog and operational data
- **Feedback Loop**: Price adjustment and effectiveness tracking

## Features

### Real-Time Monitoring
- Live shopping event stream visualization
- 1-minute aggregation windows
- Instant cannibalization alerts

### AI-Powered Insights
- Gemini Pro explains why cannibalization occurs
- Context-aware recommendations
- Confidence scoring

### Automated Actions
- Stop promotions instantly
- Adjust pricing dynamically
- Track action effectiveness

### Feedback Learning
- Measures before/after metrics
- Effectiveness scoring (0-100)
- Continuous improvement

## Quick Start

### Prerequisites

- Docker 24.0+ and Docker Compose 2.0+
- Python 3.11+ (for local development)
- Node.js 20+ (for frontend development)
- Google Gemini API Key

---

## Local Development

Run the entire system locally using Docker Compose.

### Step 1: Clone and Setup

```bash
# Clone repository
git clone https://github.com/Sai-Krishna99/truelift-ai.git
cd truelift-ai

# Copy environment template
cp .env.development .env
```

### Step 2: Configure Environment

Edit `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 3: Start Services

```bash
# Start all services with Docker
./start.sh
```

### Step 4: Access the Dashboard

| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API Docs** | http://localhost:8000/docs |

### Useful Commands

```bash
# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

---

## Production Deployment (GCP Cloud Run)

Deploy to Google Cloud Platform using Cloud Run for serverless microservices.

### Prerequisites

1. **GCP Account** with billing enabled
2. **Google Cloud SDK** installed (`brew install google-cloud-sdk`)
3. **GCP Project** created (e.g., `truelift-ai`)
4. **Cloud SQL** PostgreSQL instance
5. **Memorystore** Redis instance  
6. **Confluent Cloud** Kafka cluster
7. **VPC Connector** for Cloud Run to access private resources

### Step 1: Authenticate with GCP

```bash
gcloud auth login
gcloud config set project truelift-ai
```

### Step 2: Set Environment Variables

Export your credentials (do not commit these):

```bash
export GEMINI_API_KEY=your_gemini_api_key
export POSTGRES_HOST=your_cloud_sql_ip
export POSTGRES_DB=postgres
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_postgres_password
export REDIS_HOST=your_redis_internal_ip
export KAFKA_BOOTSTRAP_SERVERS=your_confluent_bootstrap:9092
export KAFKA_SASL_USERNAME=your_kafka_api_key
export KAFKA_SASL_PASSWORD=your_kafka_api_secret
export KAFKA_SECURITY_PROTOCOL=SASL_SSL
```

### Step 3: Deploy to Cloud Run

```bash
./deploy-gcp-cloudrun.sh
```

This script will:
1. Enable required GCP APIs
2. Store secrets in Secret Manager
3. Build and deploy all microservices to Cloud Run
4. Configure VPC connector for database access
5. Output the Frontend and Backend URLs

### Step 4: Access Deployed Services

After deployment, you'll see:

```
🎉 Deployment Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Frontend URL: https://truelift-frontend-xxxxx.run.app
Backend URL:  https://truelift-backend-xxxxx.run.app
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Cost Optimization

All services are configured with:
- **Min instances = 0** (cold starts expected)
- **Max instances capped** to prevent runaway costs
- First request after idle may take 5-15 seconds

Monitor costs at: https://console.cloud.google.com/billing

---

## Project Structure

```
truelift-ai/
├── backend/                  # FastAPI REST API
├── frontend/                 # Next.js dashboard
├── services/
│   ├── virtual-shoppers/     # Event simulator
│   ├── ml-detector/          # Cannibalization detector
│   ├── gemini-agent/         # AI strategy generator
│   └── feedback-loop/        # Action processor
├── infrastructure/           # Database schemas
├── docker-compose.yml        # Local orchestration
├── start.sh                  # Local development script
├── deploy-gcp-cloudrun.sh    # Production deployment script
├── .env.development          # Local environment template
├── .env.production.example   # Production environment template
└── README.md                 # This file
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/alerts` | List all cannibalization alerts |
| `GET` | `/alerts/{id}` | Get specific alert by ID |
| `GET` | `/promotions` | List active promotions |
| `POST` | `/actions` | Execute user actions |
| `GET` | `/actions/recent` | Get recent actions |
| `GET` | `/dashboard/stats` | Real-time statistics |
| `GET` | `/feedback` | Action effectiveness metrics |
| `POST` | `/demo/trigger` | Trigger demo simulation |
| `WS` | `/ws` | WebSocket for live updates |

## Environment Variables

See [.env.production.example](.env.production.example) for the complete list of required environment variables.

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key for AI explanations |
| `POSTGRES_HOST` | PostgreSQL database host |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `REDIS_HOST` | Redis cache host |
| `KAFKA_BOOTSTRAP_SERVERS` | Confluent Kafka bootstrap servers |
| `KAFKA_SASL_USERNAME` | Kafka API key |
| `KAFKA_SASL_PASSWORD` | Kafka API secret |

## Troubleshooting

**Error: "GEMINI_API_KEY is not set"**
- Ensure `.env` file exists with your API key
- Restart services after updating environment

**Error: "gcloud: command not found"**
- Install Google Cloud SDK: `brew install google-cloud-sdk`
- Restart terminal or run `source ~/.zshrc`

**Cold start delays in production**
- Expected with min-instances=0 for cost optimization
- First request may take 5-15 seconds after idle

**Database connection errors**
- Verify VPC connector is configured
- Check Cloud SQL instance is running
- Ensure IP ranges are correct

**Database schema errors (e.g., "column does not exist") - LOCAL ONLY**
- Reset the local database by removing the Docker volume:
```bash
docker-compose down
docker volume rm truelift-ai_postgres_data
./start.sh
```
> **Warning**: Never do this in production! Use database migrations instead.

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built for the Google Cloud + Confluent Hackathon**

*Detecting promotional cannibalization before it costs you money!*
