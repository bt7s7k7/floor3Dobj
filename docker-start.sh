#!/bin/bash

# Docker startup script for AI Floorplan Service

echo "🚀 Starting AI Floorplan to 3D Service..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with your OPENAI_API_KEY"
    echo "Example:"
    echo "OPENAI_API_KEY=your_api_key_here"
    exit 1
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=" .env; then
    echo "❌ OPENAI_API_KEY not found in .env file!"
    exit 1
fi

# Create necessary directories
mkdir -p outputs logs

echo "🔧 Building Docker image..."
docker-compose -f docker-compose.ai.yml build

echo "🚀 Starting services..."
docker-compose -f docker-compose.ai.yml up -d

echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose -f docker-compose.ai.yml ps | grep -q "Up"; then
    echo "✅ Services started successfully!"
    echo ""
    echo "🌐 API Endpoints:"
    echo "  Health Check: http://localhost:8081/health"
    echo "  Process Floorplan: POST http://localhost:8081/process-floorplan"
    echo "  Simple Process: POST http://localhost:8081/process-simple"
    echo ""
    echo "📋 Usage Examples:"
    echo "  curl -X POST -F 'image=@your_floorplan.png' http://localhost:8081/process-simple -o result.gltf"
    echo "  curl -X POST -F 'image=@your_floorplan.png' http://localhost:8081/process-floorplan -o result.zip"
    echo ""
    echo "📊 View logs:"
    echo "  docker-compose -f docker-compose.ai.yml logs -f"
    echo ""
    echo "🛑 Stop services:"
    echo "  docker-compose -f docker-compose.ai.yml down"
else
    echo "❌ Failed to start services!"
    echo "Check logs: docker-compose -f docker-compose.ai.yml logs"
fi
