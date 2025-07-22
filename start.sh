#!/bin/bash

# Simple Travel Agent Startup Script

echo "🚀 Starting Simple Travel Agent..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Please copy .env.template to .env and configure your API keys."
    echo "   cp .env.template .env"
    echo "   nano .env"
    exit 1
fi

# Start the application
echo "✅ Starting Simple Travel Agent API..."
echo "🌐 API will be available at: http://localhost:8000"
echo "📚 API documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python simple_main.py
