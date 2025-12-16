#!/bin/bash

# Script to switch between development and production environments
# Usage: ./switch-env.sh [dev|prod]

ENV_TYPE=${1:-dev}

case $ENV_TYPE in
  dev|development)
    echo "🔧 Switching to DEVELOPMENT environment..."
    cp .env.development .env
    echo "✅ Development environment activated!"
    echo ""
    echo "📋 Configuration:"
    echo "  - Local Docker services (Kafka, Postgres, Redis)"
    echo "  - Demo mode: ENABLED"
    echo "  - Event rate: 15 events/min"
    echo "  - Simulation: ENABLED"
    echo ""
    echo "🚀 To start: docker-compose up -d --build"
    ;;
    
  prod|production)
    echo "🏭 Switching to PRODUCTION environment..."
    cp .env.production .env
    echo "✅ Production environment activated!"
    echo ""
    echo "⚠️  IMPORTANT - Update .env with your production credentials:"
    echo "  - KAFKA_BOOTSTRAP_SERVERS (Confluent Cloud)"
    echo "  - KAFKA_SASL_USERNAME & KAFKA_SASL_PASSWORD"
    echo "  - POSTGRES_HOST (Cloud SQL connection)"
    echo "  - REDIS_HOST (Memorystore IP)"
    echo "  - GEMINI_API_KEY"
    echo ""
    echo "📋 Configuration:"
    echo "  - Confluent Cloud Kafka"
    echo "  - Cloud SQL Postgres"
    echo "  - Cloud Memorystore Redis"
    echo "  - Demo mode: DISABLED"
    echo "  - Event rate: 10 events/min (cost optimized)"
    echo ""
    echo "🚀 For local testing with prod config:"
    echo "   docker-compose up -d --build"
    echo ""
    echo "🚀 For GCP Cloud Run deployment:"
    echo "   ./deploy-cloudrun.sh"
    ;;
    
  *)
    echo "❌ Invalid environment type: $ENV_TYPE"
    echo ""
    echo "Usage: ./switch-env.sh [dev|prod]"
    echo ""
    echo "Options:"
    echo "  dev, development  - Switch to development environment (Docker Compose)"
    echo "  prod, production  - Switch to production environment (GCP Cloud Run)"
    exit 1
    ;;
esac
