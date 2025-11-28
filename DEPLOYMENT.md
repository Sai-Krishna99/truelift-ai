# TrueLift AI - Production Deployment Guide

This guide covers deployment and setup for the TrueLift Real-time Cannibalization Detection and Response System.

## System Architecture

The system consists of the following microservices:

1. **Virtual Shoppers** - Simulates live shopping activity
2. **Stream Events** - Kafka event streaming pipeline
3. **ML Detector** - Real-time cannibalization detection with Flink
4. **Gemini Agent** - AI-powered strategy generation
5. **Backend API** - FastAPI REST service
6. **Frontend Dashboard** - Next.js React UI
7. **Feedback Loop** - Price adjustment and monitoring

## Prerequisites

- Docker 24.0+ and Docker Compose 2.0+
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local service development)
- 8GB+ RAM recommended
- Google Gemini API Key

## Quick Start

### 1. Clone and Setup Environment

```bash
cd truelift-ai
cp .env.example .env
```

Edit `.env` and add your Gemini API key:
```
GEMINI_API_KEY=your_actual_api_key_here
```

### 2. Start All Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Kafka + Zookeeper (ports 9092, 9094)
- All microservices
- Backend API (port 8000)
- Frontend Dashboard (port 3000)

### 3. Access the Dashboard

Open your browser to: **http://localhost:3000**

### 4. Verify Services

Check all services are running:
```bash
docker-compose ps
```

Check backend health:
```bash
curl http://localhost:8000/health
```

## Service Details

### Virtual Shoppers Simulator
- Generates 8-15 shopping events per minute per promotion
- Simulates realistic cannibalization patterns
- Publishes events to `shopping-events` Kafka topic

### ML Detector
- Aggregates sales in 1-minute windows
- Compares actual vs predicted sales
- Uses Isolation Forest for anomaly detection
- Triggers alerts when cannibalization detected

### Gemini Pro Agent
- Listens to cannibalization alerts
- Generates AI explanations and strategies
- Provides primary recommendation + alternatives
- Stores strategies in Redis and PostgreSQL

### Backend API
- FastAPI with WebSocket support for real-time updates
- REST endpoints for alerts, promotions, actions
- Handles user actions (stop promo, adjust price)
- Dashboard statistics and feedback queries

### Frontend Dashboard
- Real-time alert monitoring
- AI strategy display
- One-click action execution
- Live statistics and metrics

### Feedback Loop
- Monitors action effectiveness
- Calculates before/after sales metrics
- Adjusts prices based on strategies
- Records effectiveness scores

## API Endpoints

### Alerts
```bash
GET  /alerts                    # List all alerts
GET  /alerts/{alert_id}         # Get specific alert
GET  /alerts?status=pending     # Filter by status
```

### Promotions
```bash
GET  /promotions                # List all promotions
GET  /promotions?is_active=true # Active promotions only
```

### Actions
```bash
POST /actions                   # Execute user action
{
  "alert_id": "ALERT-PROMO001-...",
  "promo_id": "PROMO001",
  "action_type": "stop_promotion",
  "performed_by": "manager"
}
```

### Dashboard
```bash
GET  /dashboard/stats           # Real-time statistics
GET  /feedback                  # Feedback loop results
```

### WebSocket
```bash
WS   /ws                        # Real-time updates
```

## Database Schema

### Tables
- `promotions` - Active and historical promotions
- `sales_events` - All shopping events
- `cannibalization_alerts` - Detected issues
- `ai_strategies` - Gemini-generated recommendations
- `user_actions` - Manager decisions
- `feedback_loop` - Action effectiveness tracking

## Development

### Run Individual Services Locally

#### Virtual Shoppers
```bash
cd services/virtual-shoppers
pip install -r requirements.txt
python simulator.py
```

#### ML Detector
```bash
cd services/ml-detector
pip install -r requirements.txt
python detector.py
```

#### Gemini Agent
```bash
cd services/gemini-agent
export GEMINI_API_KEY=your_key
pip install -r requirements.txt
python agent.py
```

#### Backend API
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Monitoring and Logs

### View logs for all services
```bash
docker-compose logs -f
```

### View specific service logs
```bash
docker-compose logs -f virtual-shoppers
docker-compose logs -f ml-detector
docker-compose logs -f gemini-agent
docker-compose logs -f backend-api
```

### Check Kafka topics
```bash
docker exec -it truelift-kafka kafka-topics --list --bootstrap-server localhost:9092
```

### Monitor Kafka messages
```bash
docker exec -it truelift-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic shopping-events \
  --from-beginning
```

## Troubleshooting

### Services not starting
```bash
docker-compose down -v
docker-compose up -d
```

### Database connection issues
```bash
docker-compose restart postgres
docker-compose logs postgres
```

### Kafka connection issues
```bash
docker-compose restart zookeeper kafka
docker-compose logs kafka
```

### Frontend not loading
```bash
docker-compose restart frontend
docker-compose logs frontend
```

## Production Considerations

### Security
- Change default database credentials
- Use environment-specific API keys
- Enable HTTPS for frontend and backend
- Implement API authentication
- Set up network policies

### Scaling
- Use Confluent Cloud for Kafka
- Deploy services to Kubernetes
- Use managed PostgreSQL (RDS, Cloud SQL)
- Use Redis Cluster for high availability
- Implement load balancing

### Monitoring
- Add Prometheus metrics
- Set up Grafana dashboards
- Configure log aggregation (ELK, Datadog)
- Set up alerting (PagerDuty, Opsgenie)

### Backup
- Configure PostgreSQL backups
- Back up Kafka topics
- Store ML models in S3/GCS

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `POSTGRES_HOST` | PostgreSQL hostname | localhost |
| `POSTGRES_DB` | Database name | truelift |
| `POSTGRES_USER` | Database user | truelift_user |
| `POSTGRES_PASSWORD` | Database password | truelift_pass |
| `REDIS_HOST` | Redis hostname | localhost |
| `REDIS_PORT` | Redis port | 6379 |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka servers | localhost:9094 |
| `NEXT_PUBLIC_API_URL` | Backend API URL | http://localhost:8000 |

## Testing

### Test the full workflow
1. Start all services
2. Check virtual shoppers generating events
3. Wait for ML detector to identify cannibalization
4. Verify alert appears on dashboard
5. Check Gemini strategy is generated
6. Execute action (stop promotion)
7. Verify feedback loop records effectiveness

### Manual testing
```bash
curl http://localhost:8000/alerts | jq
curl http://localhost:8000/promotions | jq
curl http://localhost:8000/dashboard/stats | jq
```

## Stopping Services

```bash
docker-compose down
```

To also remove volumes:
```bash
docker-compose down -v
```

## Support

For issues and questions:
- Check logs: `docker-compose logs`
- Verify health: `curl http://localhost:8000/health`
- Review architecture diagrams in README.md

## License

See LICENSE file for details.
