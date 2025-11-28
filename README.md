# TrueLift AI

Real-time promotional cannibalization detection and automated response system using AI/ML.

## Overview

TrueLift AI is a production-grade system that:
- **Detects** promotional cannibalization in real-time using ML models
- **Explains** the causes using Gemini Pro AI
- **Recommends** strategic actions automatically
- **Responds** with adaptive pricing and promotion adjustments
- **Learns** from feedback to improve over time

## High Level Workflow

<img width="2628" height="1062" alt="workflow" src="https://github.com/user-attachments/assets/51a41595-c688-44d3-b599-4cb8c302b2f5" />
<img width="438" height="1181" alt="image" src="https://github.com/user-attachments/assets/0fd942ed-538a-4714-afa9-259b72e96c80" />

## Architecture and Technical Overview

<img width="1626" height="4062" alt="architecture" src="https://github.com/user-attachments/assets/4a466576-ed41-4880-aa94-e3940e34f325" />
<img width="798" height="1307" alt="image" src="https://github.com/user-attachments/assets/8b8cb652-a912-4aa6-9dae-85a6ff9d51fd" />

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
- **TrueLift Dashboard**: Next.js real-time UI (also supports Streamlit/Gradio)
- **Backend API**: FastAPI REST service
- **Cloud SQL**: Product catalog and operational data
- **Feedback Loop**: Price adjustment and effectiveness tracking

## Technology Stack

### Cloud Platform
- Google Cloud Platform (GCP)
- Confluent Cloud for Kafka

### Machine Learning
- Vertex AI AutoML (Tabular)
- XGBoost / LightGBM
- Isolation Forest for anomaly detection
- Google Gemini Pro for AI reasoning

### Data & Streaming
- BigQuery for analytics
- Cloud SQL (PostgreSQL) for operational data
- Apache Kafka (Confluent Cloud)
- Apache Flink for stream processing
- Redis for caching

### Backend
- Python 3.11+
- FastAPI for REST API
- Flask for inference service
- WebSocket for real-time updates

### Frontend
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Optional: Streamlit/Gradio

### DevOps
- Docker & Docker Compose
- Cloud Run for serverless deployment
- GitHub Actions for CI/CD

## Quick Start

### Local Development (Docker)

```bash
# Clone repository
git clone https://github.com/Sai-Krishna99/truelift-ai.git
cd truelift-ai

# Setup environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Start all services
./start.sh

# Access dashboard
open http://localhost:3000
```

### Google Cloud Platform Deployment

```bash
# Setup GCP project
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=us-central1

# Deploy infrastructure
./deploy-gcp.sh

# Train ML model
cd ml-models
python train_pipeline.py

# Update .env with Vertex AI endpoint ID
# Deploy application services
docker-compose up -d
```

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

## Project Structure

```
truelift-ai/
├── backend/              # FastAPI REST API
├── frontend/             # Next.js dashboard
├── ml-models/            # ML training & inference
│   ├── bigquery_integration.py
│   ├── vertex_ai_integration.py
│   ├── inference_service.py
│   └── train_pipeline.py
├── services/
│   ├── virtual-shoppers/ # Event simulator
│   ├── ml-detector/      # Cannibalization detector
│   ├── gemini-agent/     # AI strategy generator
│   └── feedback-loop/    # Action processor
├── infrastructure/       # Database schemas
├── docker-compose.yml    # Local orchestration
├── deploy-gcp.sh        # GCP deployment
└── start.sh             # Quick start script
```

## API Endpoints

- `GET /alerts` - List cannibalization alerts
- `GET /promotions` - Active promotions
- `POST /actions` - Execute user actions
- `GET /dashboard/stats` - Real-time statistics
- `GET /feedback` - Action effectiveness
- `WS /ws` - WebSocket for live updates

## Development

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed setup instructions.

## License

See [LICENSE](LICENSE) file for details.
