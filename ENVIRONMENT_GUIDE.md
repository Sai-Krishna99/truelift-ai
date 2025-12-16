# Environment Configuration Guide

## Overview
TrueLift AI supports two environments:
- **Development**: Local Docker Compose with demo mode enabled
- **Production**: GCP Cloud Run with Confluent Cloud Kafka and managed services

## Quick Toggle

### Switch to Development Mode
```bash
./switch-env.sh dev
docker-compose up -d --build
```

### Switch to Production Mode
```bash
./switch-env.sh prod
# Edit .env with your production credentials
docker-compose up -d --build  # For local testing
# OR
./deploy-cloudrun.sh  # For GCP deployment
```

## Environment Differences

### Development Environment (`.env.development`)
- **Kafka**: Local Docker container
- **Database**: Local PostgreSQL
- **Redis**: Local Docker container
- **Demo Mode**: `ENABLED` (demo burst button works)
- **Event Rate**: 15 events/minute per promotion
- **Simulation**: Always on
- **Cost**: Free (local resources only)

### Production Environment (`.env.production`)
- **Kafka**: Confluent Cloud (SASL_SSL)
- **Database**: GCP Cloud SQL
- **Redis**: GCP Cloud Memorystore
- **Demo Mode**: `DISABLED` (no demo bursts)
- **Event Rate**: 10 events/minute (cost optimized)
- **Simulation**: Controllable via `SIMULATION_ENABLED`
- **Cost**: Pay-per-use GCP services

## Configuration Variables

### Key Toggles

| Variable | Development | Production | Purpose |
|----------|-------------|------------|---------|
| `DEMO_MODE` | `true` | `false` | Enable/disable demo burst functionality |
| `SIMULATION_ENABLED` | `true` | `true` | Control virtual shopper event generation |
| `EVENT_RATE_PER_MINUTE` | `15` | `10` | Events per promotion per minute |

### Simulation Control

To **pause** event generation in production (reduce Kafka costs):
```bash
# In .env or Cloud Run environment variables
SIMULATION_ENABLED=false
```

To **resume** event generation:
```bash
SIMULATION_ENABLED=true
```

To **adjust** event rate (lower = less cost):
```bash
EVENT_RATE_PER_MINUTE=5  # Reduce from 10 to 5
```

## Production Setup Checklist

### 1. Configure Confluent Cloud Kafka
```bash
# Update in .env
KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.us-central1.gcp.confluent.cloud:9092
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
KAFKA_SASL_USERNAME=your-kafka-api-key
KAFKA_SASL_PASSWORD=your-kafka-api-secret
```

Run topic configuration:
```bash
./scripts/configure-confluent-topics.sh
```

### 2. Configure GCP Cloud SQL
```bash
# Update in .env
POSTGRES_HOST=/cloudsql/project-id:region:instance-name
POSTGRES_DB=truelift
POSTGRES_USER=truelift_user
POSTGRES_PASSWORD=<from-secret-manager>
```

### 3. Configure GCP Memorystore Redis
```bash
# Update in .env with internal IP
REDIS_HOST=10.x.x.x
REDIS_PORT=6379
```

### 4. Configure Gemini API
```bash
# Update in .env or use Secret Manager
GEMINI_API_KEY=your-actual-api-key
```

### 5. Deploy to Cloud Run
```bash
./deploy-cloudrun.sh
```

## Environment Variable Priority

When running locally:
1. `.env` file (created by `switch-env.sh`)
2. `docker-compose.yml` defaults

When running on Cloud Run:
1. Cloud Run environment variables
2. Secret Manager references
3. Default values in code

## Testing Production Config Locally

You can test production configuration locally before deploying:

```bash
# Switch to production config
./switch-env.sh prod

# Update .env with production credentials
# (Use read-only test credentials if available)

# Start services locally
docker-compose up -d --build

# Services will connect to production Kafka/DB/Redis
```

⚠️ **Warning**: Be careful when testing locally with production credentials. Consider using separate test/staging resources.

## Cost Optimization Strategies

### Pause During Off-Hours
```bash
# Stop simulation at night
SIMULATION_ENABLED=false

# Resume in the morning
SIMULATION_ENABLED=true
```

### Scale Down Event Rate
```bash
# Reduce events during low-traffic periods
EVENT_RATE_PER_MINUTE=5  # or lower
```

### Use GCP min-instances=0
Cloud Run services are configured with `min-instances=0`:
- Services scale to zero when idle
- Cold starts when traffic resumes (~5-10 seconds)
- Significant cost savings for non-production workloads

### Confluent Cloud Basic Cluster
- Use Basic cluster for dev/staging
- Use Standard/Dedicated for production
- Monitor usage via Confluent Cloud dashboard

## Monitoring

### Check Current Environment
```bash
cat .env | grep -E "DEMO_MODE|SIMULATION_ENABLED|KAFKA_BOOTSTRAP_SERVERS"
```

### Verify Simulation Status
```bash
docker-compose logs virtual-shoppers | tail -20
```

### Check Event Rate
```bash
# Count events in last minute
docker-compose logs virtual-shoppers --since=1m | grep -c "bought"
```

## Troubleshooting

### Demo Button Not Working
- Check: `DEMO_MODE=true` in `.env`
- Restart: `docker-compose restart backend-api virtual-shoppers`

### No Events Being Generated
- Check: `SIMULATION_ENABLED=true` in `.env`
- Check logs: `docker-compose logs virtual-shoppers`
- Verify Kafka: `docker-compose logs kafka`

### Production Connection Errors
- Verify Confluent Cloud credentials
- Check Cloud SQL connection string
- Confirm Memorystore IP is accessible
- Review GCP VPC/firewall rules

## Additional Resources

- [GCP Deployment Guide](./GCP_DEPLOYMENT_GUIDE.md)
- [Enhancements Summary](./ENHANCEMENTS_SUMMARY.md)
- [Deployment Instructions](./DEPLOYMENT.md)
