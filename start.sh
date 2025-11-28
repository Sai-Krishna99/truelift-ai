#!/bin/bash

set -e

echo "🚀 Starting TrueLift AI System..."

if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your GEMINI_API_KEY before continuing."
    exit 1
fi

if ! grep -q "GEMINI_API_KEY=your_gemini_api_key_here" .env; then
    echo "✓ Environment configured"
else
    echo "⚠️  Please set your GEMINI_API_KEY in .env file"
    exit 1
fi

echo "📦 Building Docker images..."
docker-compose build

echo "🔧 Starting infrastructure services..."
docker-compose up -d postgres redis zookeeper kafka

echo "⏳ Waiting for services to be ready..."
sleep 10

echo "🏃 Starting application services..."
docker-compose up -d

echo "⏳ Waiting for all services to initialize..."
sleep 15

echo ""
echo "✅ TrueLift AI is now running!"
echo ""
echo "📊 Dashboard:    http://localhost:3000"
echo "🔌 Backend API:  http://localhost:8000"
echo "📖 API Docs:     http://localhost:8000/docs"
echo ""
echo "📝 View logs:    docker-compose logs -f"
echo "🛑 Stop system:  docker-compose down"
echo ""

docker-compose ps
