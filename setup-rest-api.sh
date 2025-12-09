#!/bin/bash

# PR Agent REST API Setup Script
# This script helps set up and run the PR Agent REST API server

set -e

echo "=========================================="
echo "PR Agent REST API Setup"
echo "=========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "✗ pip3 is not installed. Please install Python 3.9+ with pip."
    exit 1
fi
echo "✓ pip3 is installed"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install fastapi uvicorn pydantic python-dotenv
echo "✓ Dependencies installed"

# Install PR Agent
echo "Installing PR Agent..."
pip install -e .
echo "✓ PR Agent installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file..."
    cat > .env << EOF
# GitHub Configuration
GITHUB_TOKEN=your_github_token_here

# AI Model Configuration
OPENAI_KEY=your_openai_key_here

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Optional: Other LLM providers
# ANTHROPIC_KEY=your_anthropic_key
# GOOGLE_API_KEY=your_google_api_key
EOF
    echo "✓ .env file created"
    echo "⚠ Please update .env with your actual credentials"
else
    echo "✓ .env file already exists"
fi

# Create directories if they don't exist
mkdir -p logs

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update .env with your credentials:"
echo "   - GITHUB_TOKEN: Your GitHub personal access token"
echo "   - OPENAI_KEY: Your OpenAI API key"
echo ""
echo "2. Start the server:"
echo "   source venv/bin/activate"
echo "   python -m pr_agent.servers.rest_api_server"
echo ""
echo "3. Access the API:"
echo "   Browser:  http://localhost:8000/docs"
echo "   Health:   http://localhost:8000/health"
echo ""
echo "4. Or use Docker:"
echo "   docker-compose up -d"
echo ""
