#!/bin/bash
# Run the AutoGen platform locally without Docker

echo "🚀 Starting AutoGen Platform locally..."

# Check Python version
python_version=$(python3 --version 2>&1)
echo "Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start Redis in background (if available)
if command -v redis-server &> /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
else
    echo "⚠️  Redis not found. Please install Redis or run in Docker"
    echo "To install Redis: sudo apt-get install redis-server"
fi

# Export environment variables
export $(cat .env | grep -v '^#' | xargs)

# Run the application
echo "Starting FastAPI application..."
echo "-----------------------------------"
echo "🌐 UI will be available at: http://localhost:8000"
echo "📚 API docs at: http://localhost:8000/docs"
echo "❤️  Health check at: http://localhost:8000/health"
echo "-----------------------------------"
echo "Press Ctrl+C to stop"
echo ""

# Run with uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload