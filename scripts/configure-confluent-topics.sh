#!/bin/bash

# Confluent Cloud Topic Configuration for Cost Optimization
# This script configures Kafka topics with minimal retention and partition settings

set -e

echo "========================================"
echo "Confluent Cloud - Cost Control Setup"
echo "========================================"
echo ""

# Check if confluent CLI is installed
if ! command -v confluent &> /dev/null; then
    echo "Error: confluent CLI not found."
    echo "Install from: https://docs.confluent.io/confluent-cli/current/install.html"
    exit 1
fi

# Login to Confluent Cloud
echo "Logging into Confluent Cloud..."
confluent login

# Select environment and cluster
echo "Please select your Confluent Cloud environment and cluster:"
confluent environment list
read -p "Enter environment ID: " ENV_ID
confluent environment use $ENV_ID

confluent kafka cluster list
read -p "Enter cluster ID: " CLUSTER_ID
confluent kafka cluster use $CLUSTER_ID

# Configure API key
read -p "Enter API Key: " API_KEY
read -sp "Enter API Secret: " API_SECRET
echo ""
confluent api-key use $API_KEY --resource $CLUSTER_ID

echo ""
echo "Creating topics with cost-optimized settings..."
echo ""

# Topic configuration for cost optimization
# - Single partition (minimum for ordering)
# - 1-hour retention (3600000 ms)
# - Cleanup policy: delete (remove old messages)
# - Compression: snappy (reduce storage)

# Create shopping-events topic
echo "Creating 'shopping-events' topic..."
confluent kafka topic create shopping-events \
    --partitions 1 \
    --config retention.ms=3600000 \
    --config cleanup.policy=delete \
    --config compression.type=snappy \
    --config min.insync.replicas=1 \
    || echo "Topic 'shopping-events' may already exist"

# Create cannibalization-alerts topic
echo "Creating 'cannibalization-alerts' topic..."
confluent kafka topic create cannibalization-alerts \
    --partitions 1 \
    --config retention.ms=3600000 \
    --config cleanup.policy=delete \
    --config compression.type=snappy \
    --config min.insync.replicas=1 \
    || echo "Topic 'cannibalization-alerts' may already exist"

# Create user-actions topic
echo "Creating 'user-actions' topic..."
confluent kafka topic create user-actions \
    --partitions 1 \
    --config retention.ms=3600000 \
    --config cleanup.policy=delete \
    --config compression.type=snappy \
    --config min.insync.replicas=1 \
    || echo "Topic 'user-actions' may already exist"

echo ""
echo "========================================"
echo "Topic Configuration Complete"
echo "========================================"
echo ""
echo "Cost Optimization Settings Applied:"
echo "  ✓ Partitions: 1 per topic (minimum)"
echo "  ✓ Retention: 1 hour (reduces storage)"
echo "  ✓ Compression: Snappy (reduces bandwidth)"
echo "  ✓ Min ISR: 1 (single replica for basic tier)"
echo ""
echo "Additional Cost Controls:"
echo ""
echo "1. Pause Virtual Shoppers (stop event generation):"
echo "   export SIMULATION_ENABLED=false"
echo ""
echo "2. Reduce Event Rate (lower throughput):"
echo "   export EVENT_RATE_PER_MINUTE=5"
echo ""
echo "3. Monitor usage in Confluent Cloud Console:"
echo "   https://confluent.cloud/"
echo ""
echo "4. Set up billing alerts:"
echo "   Account Settings → Billing → Set Budget Alert"
echo ""

# Display topic configurations
echo "Current Topic Configurations:"
echo ""
confluent kafka topic list
echo ""

for topic in shopping-events cannibalization-alerts user-actions; do
    echo "Topic: $topic"
    confluent kafka topic describe $topic | grep -E "(Partition|retention|cleanup|compression)" || true
    echo ""
done

echo "Setup complete! 🎉"
