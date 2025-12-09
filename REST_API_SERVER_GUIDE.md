# PR Agent REST API Server Guide

A comprehensive guide to hosting PR Agent as a REST API service with multiple endpoints for PR review, description, improvements, issues detection, and more.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Running the Server](#running-the-server)
4. [API Endpoints](#api-endpoints)
5. [Usage Examples](#usage-examples)
6. [Configuration](#configuration)
7. [Deployment](#deployment)
8. [Docker Setup](#docker-setup)
9. [Advanced Features](#advanced-features)

## Quick Start

### 1. Install Dependencies

```bash
pip install fastapi uvicorn pydantic python-dotenv
pip install -e .  # Install PR Agent
```

### 2. Set Environment Variables

```bash
export GITHUB_TOKEN=your_github_token_here
export OPENAI_KEY=your_openai_key_here  # or LiteLLM provider
```

### 3. Start the Server

```bash
python -m pr_agent.servers.rest_api_server
# or with uvicorn
uvicorn pr_agent.servers.rest_api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Capabilities**: http://localhost:8000/api/v1/capabilities

## Installation

### Prerequisites

- Python 3.9+
- Git
- GitHub token (for private repos)
- OpenAI API key or other LLM provider

### Step 1: Clone and Setup

```bash
git clone https://github.com/Codium-ai/pr-agent.git
cd pr-agent
pip install -e .
pip install fastapi uvicorn python-dotenv
```

### Step 2: Configure Credentials

Create a `.env` file or set environment variables:

```bash
# .env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
OPENAI_KEY=sk-xxxxxxxxxxxx

# Optional
LOG_LEVEL=INFO
PORT=8000
HOST=0.0.0.0
```

Or set via environment:

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
export OPENAI_KEY="sk-xxxxxxxxxxxx"
```

## Running the Server

### Development Mode

```bash
# With auto-reload
uvicorn pr_agent.servers.rest_api_server:app --reload --port 8000

# Or directly
python -m pr_agent.servers.rest_api_server
```

### Production Mode

```bash
# Using gunicorn with multiple workers
gunicorn pr_agent.servers.rest_api_server:app --workers 4 --bind 0.0.0.0:8000

# Or using uvicorn with multiple workers
uvicorn pr_agent.servers.rest_api_server:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Health Check

```
GET /health
```

Returns server status and version.

**Response:**
```json
{
  "status": "healthy",
  "service": "PR Agent REST API",
  "version": "1.0.0"
}
```

### PR Review

```
POST /api/v1/review
```

Perform comprehensive AI-powered code review.

**Request:**
```json
{
  "pr_url": "https://github.com/owner/repo/pull/123",
  "extra_instructions": "Focus on security aspects",
  "ai_temperature": 0.7
}
```

**Response:**
```json
{
  "status": "success",
  "message": "PR review completed",
  "pr_url": "https://github.com/owner/repo/pull/123"
}
```

### PR Description

```
POST /api/v1/describe
```

Generate AI-powered PR description.

**Request:**
```json
{
  "pr_url": "https://github.com/owner/repo/pull/123",
  "extra_instructions": "Include API changes"
}
```

### Code Improvements

```
POST /api/v1/improve
```

Generate code improvement suggestions.

**Request:**
```json
{
  "pr_url": "https://github.com/owner/repo/pull/123",
  "extra_instructions": "Prioritize performance optimizations"
}
```

### Issues Detection

```
POST /api/v1/issues
```

Detect potential issues and bugs.

**Request:**
```json
{
  "pr_url": "https://github.com/owner/repo/pull/123",
  "severity": "critical"  // all, critical, major, minor
}
```

### Ask Questions

```
POST /api/v1/ask
```

Ask specific questions about a PR.

**Request:**
```json
{
  "pr_url": "https://github.com/owner/repo/pull/123",
  "question": "Is this backward compatible?"
}
```

### Batch Processing

```
POST /api/v1/batch
```

Process multiple PRs in a repository.

**Request:**
```json
{
  "repo_url": "https://github.com/owner/repo",
  "action": "review",  // review, describe, improve, issues
  "max_prs": 5,
  "extra_instructions": "Focus on critical issues"
}
```

### Async Endpoints

All endpoints have async versions that return immediately with a job ID:

- `POST /api/v1/review/async`
- `POST /api/v1/describe/async`
- `POST /api/v1/improve/async`

**Response:**
```json
{
  "status": "queued",
  "job_id": "review_123",
  "message": "Review queued for processing"
}
```

## Usage Examples

### Example 1: Review a PR

```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123"
  }'
```

### Example 2: Generate Description

```bash
curl -X POST http://localhost:8000/api/v1/describe \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123",
    "extra_instructions": "Include impact analysis"
  }'
```

### Example 3: Get Improvement Suggestions

```bash
curl -X POST http://localhost:8000/api/v1/improve \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123"
  }'
```

### Example 4: Python Client

```python
import requests

BASE_URL = "http://localhost:8000"

def review_pr(pr_url):
    response = requests.post(
        f"{BASE_URL}/api/v1/review",
        json={"pr_url": pr_url}
    )
    return response.json()

def describe_pr(pr_url):
    response = requests.post(
        f"{BASE_URL}/api/v1/describe",
        json={"pr_url": pr_url}
    )
    return response.json()

def get_improvements(pr_url):
    response = requests.post(
        f"{BASE_URL}/api/v1/improve",
        json={"pr_url": pr_url}
    )
    return response.json()

# Usage
result = review_pr("https://github.com/owner/repo/pull/123")
print(result)
```

### Example 5: JavaScript/Node.js Client

```javascript
const BASE_URL = "http://localhost:8000";

async function reviewPR(prUrl) {
  const response = await fetch(`${BASE_URL}/api/v1/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pr_url: prUrl })
  });
  return response.json();
}

async function describePR(prUrl) {
  const response = await fetch(`${BASE_URL}/api/v1/describe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pr_url: prUrl })
  });
  return response.json();
}

async function getImprovements(prUrl) {
  const response = await fetch(`${BASE_URL}/api/v1/improve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pr_url: prUrl })
  });
  return response.json();
}

// Usage
const result = await reviewPR("https://github.com/owner/repo/pull/123");
console.log(result);
```

## Configuration

### Via Environment Variables

```bash
# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# GitHub
GITHUB_TOKEN=your_token
GITHUB_URL=https://github.com

# AI Model
OPENAI_KEY=sk-xxxxx
AI_MODEL=gpt-4
AI_TEMPERATURE=0.7

# Azure DevOps (optional)
AZURE_DEVOPS_TOKEN=your_token
```

### Via Configuration File

Edit `pr_agent.toml`:

```toml
[github]
user_token = "your_token"

[config]
ai_model = "gpt-4"
ai_temperature = 0.7
log_level = "INFO"

[pr_reviewer]
extra_instructions = "Focus on security"

[pr_description]
extra_instructions = ""

[pr_code_suggestions]
extra_instructions = ""
```

## Deployment

### Option 1: systemd Service (Linux)

Create `/etc/systemd/system/pr-agent.service`:

```ini
[Unit]
Description=PR Agent REST API
After=network.target

[Service]
Type=simple
User=pr-agent
WorkingDirectory=/opt/pr-agent
Environment="GITHUB_TOKEN=your_token"
Environment="OPENAI_KEY=your_key"
ExecStart=/usr/bin/python -m pr_agent.servers.rest_api_server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start the service:

```bash
sudo systemctl start pr-agent
sudo systemctl status pr-agent
sudo journalctl -u pr-agent -f
```

### Option 2: Screen/tmux (Development)

```bash
# Using screen
screen -S pr-agent
python -m pr_agent.servers.rest_api_server
# Detach: Ctrl-A D
# Re-attach: screen -r pr-agent

# Using tmux
tmux new-session -d -s pr-agent
tmux send-keys -t pr-agent "python -m pr_agent.servers.rest_api_server" Enter
tmux attach -t pr-agent
```

## Docker Setup

### Build Docker Image

```bash
cd pr-agent
docker build -t pr-agent-api:latest -f docker/Dockerfile.api .
```

### Run Container

```bash
docker run -d \
  -p 8000:8000 \
  -e GITHUB_TOKEN=your_token \
  -e OPENAI_KEY=your_key \
  -e LOG_LEVEL=INFO \
  --name pr-agent-api \
  pr-agent-api:latest
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  pr-agent-api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - OPENAI_KEY=${OPENAI_KEY}
      - LOG_LEVEL=INFO
      - PORT=8000
      - HOST=0.0.0.0
    volumes:
      - ./pr_agent:/app/pr_agent
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Start with Docker Compose:

```bash
docker-compose up -d
docker-compose logs -f pr-agent-api
```

### Dockerfile

Create `docker/Dockerfile.api`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn

# Copy source
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run server
CMD ["python", "-m", "pr_agent.servers.rest_api_server"]
```

## Advanced Features

### 1. Custom AI Instructions

```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123",
    "extra_instructions": "1. Check for OWASP top 10 issues\n2. Verify input validation\n3. Check for SQL injection\n4. Validate API security"
  }'
```

### 2. Temperature Control

```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123",
    "ai_temperature": 0.3
  }'
```

### 3. Batch Processing

```bash
curl -X POST http://localhost:8000/api/v1/batch \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/owner/repo",
    "action": "review",
    "max_prs": 10,
    "extra_instructions": "Focus on critical issues"
  }'
```

### 4. Integration with CI/CD

#### GitHub Actions

```yaml
name: PR Review with PR Agent

on: [pull_request]

jobs:
  pr-review:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger PR Review
        run: |
          curl -X POST https://your-pr-agent-server/api/v1/review \
            -H "Content-Type: application/json" \
            -d '{
              "pr_url": "${{ github.event.pull_request.html_url }}"
            }'
```

#### GitLab CI

```yaml
pr_review:
  stage: review
  script:
    - curl -X POST https://your-pr-agent-server/api/v1/review \
        -H "Content-Type: application/json" \
        -d '{
          "pr_url": "$CI_MERGE_REQUEST_PROJECT_URL/-/merge_requests/$CI_MERGE_REQUEST_IID"
        }'
```

## Monitoring and Logs

### View Logs

```bash
# Docker
docker logs pr-agent-api -f

# systemd
journalctl -u pr-agent -f

# Direct
tail -f logs/pr-agent.log
```

### Metrics

The API exposes basic metrics at `/metrics` (requires Prometheus middleware installation):

```bash
pip install prometheus-client
```

## Troubleshooting

### Issue: "GITHUB_TOKEN not found"

**Solution:**
```bash
export GITHUB_TOKEN="your_github_token"
python -m pr_agent.servers.rest_api_server
```

### Issue: "OpenAI API key not found"

**Solution:**
```bash
export OPENAI_KEY="sk-your-key"
python -m pr_agent.servers.rest_api_server
```

### Issue: Connection refused

**Solution:**
- Check if port 8000 is available: `lsof -i :8000`
- Change port: `PORT=8001 python -m pr_agent.servers.rest_api_server`

### Issue: PR URL not recognized

**Solution:**
- Ensure URL is in format: `https://github.com/owner/repo/pull/123`
- Verify GitHub token has access to the repository

## Next Steps

1. **Customize endpoints** - Modify `rest_api_server.py` for your needs
2. **Add authentication** - Implement API key or OAuth2
3. **Add webhooks** - Listen for GitHub/GitLab webhook events
4. **Deploy to cloud** - Use AWS, GCP, Azure, or Heroku
5. **Add database** - Store results and create dashboards
6. **Add notifications** - Slack, Teams, email integration

## Support

For issues and feature requests, visit: https://github.com/Codium-ai/pr-agent/issues
