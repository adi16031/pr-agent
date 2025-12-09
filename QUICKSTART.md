# PR Agent REST API - Quick Start Guide

Get PR Agent running as a REST API server in minutes!

## 5-Minute Setup

### 1. Install & Configure

```bash
cd pr-agent

# Run setup script
chmod +x setup-rest-api.sh
./setup-rest-api.sh

# Update .env with your credentials
nano .env
```

In `.env`:
```
GITHUB_TOKEN=ghp_your_token_here
OPENAI_KEY=sk-your_key_here
```

### 2. Start the Server

```bash
source venv/bin/activate
python -m pr_agent.servers.rest_api_server
```

Output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. Test the API

#### Browser
Open: http://localhost:8000/docs

#### Command Line
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "PR Agent REST API",
  "version": "1.0.0"
}
```

## Basic Examples

### Review a PR

```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123"
  }'
```

### Generate PR Description

```bash
curl -X POST http://localhost:8000/api/v1/describe \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123"
  }'
```

### Get Code Improvements

```bash
curl -X POST http://localhost:8000/api/v1/improve \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123"
  }'
```

### Detect Issues

```bash
curl -X POST http://localhost:8000/api/v1/issues \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123",
    "severity": "critical"
  }'
```

## Docker Quick Start

### Using Docker

```bash
# Build image
docker build -t pr-agent-api:latest -f docker/Dockerfile.api .

# Run container
docker run -d \
  -p 8000:8000 \
  -e GITHUB_TOKEN="your_token" \
  -e OPENAI_KEY="your_key" \
  --name pr-agent-api \
  pr-agent-api:latest

# Check logs
docker logs -f pr-agent-api
```

### Using Docker Compose

```bash
# Create .env file
cat > .env << EOF
GITHUB_TOKEN=your_token
OPENAI_KEY=your_key
EOF

# Start services
docker-compose up -d

# View logs
docker-compose logs -f pr-agent-api

# Stop
docker-compose down
```

## Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | Interactive API documentation |
| GET | `/api/v1/capabilities` | List available features |
| POST | `/api/v1/review` | Review a PR |
| POST | `/api/v1/review/async` | Async PR review |
| POST | `/api/v1/describe` | Generate PR description |
| POST | `/api/v1/describe/async` | Async description generation |
| POST | `/api/v1/improve` | Get code improvements |
| POST | `/api/v1/improve/async` | Async improvements |
| POST | `/api/v1/issues` | Detect issues |
| POST | `/api/v1/ask` | Ask questions about PR |
| POST | `/api/v1/batch` | Process multiple PRs |

## Configuration

### Environment Variables

```bash
# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# GitHub
GITHUB_TOKEN=ghp_xxxx

# AI Model
OPENAI_KEY=sk-xxxx
AI_MODEL=gpt-4
AI_TEMPERATURE=0.7
```

### Config File

Edit `pr_agent.toml` for advanced settings:

```toml
[github]
user_token = "your_token"

[config]
ai_model = "gpt-4"
ai_temperature = 0.7

[pr_reviewer]
extra_instructions = "Focus on security"
```

## Using the Client Library

```python
from examples.pr_agent_client import PRAgentClient

client = PRAgentClient("http://localhost:8000")

# Review a PR
result = client.review_pr("https://github.com/owner/repo/pull/123")
print(result)

# Describe a PR
result = client.describe_pr("https://github.com/owner/repo/pull/123")
print(result)

# Get improvements
result = client.improve_code("https://github.com/owner/repo/pull/123")
print(result)
```

## Advanced Features

### Custom Instructions

```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123",
    "extra_instructions": "Check for SQL injection vulnerabilities"
  }'
```

### Async Operations

Start long-running tasks and check status later:

```bash
# Start async review
curl -X POST http://localhost:8000/api/v1/review/async \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/123"}'

# Response:
# {
#   "status": "queued",
#   "job_id": "review_123",
#   "message": "Review queued for processing"
# }
```

### Batch Processing

```bash
curl -X POST http://localhost:8000/api/v1/batch \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/owner/repo",
    "action": "review",
    "max_prs": 10
  }'
```

## Integration Examples

### GitHub Actions

```yaml
name: PR Review with PR Agent

on: [pull_request]

jobs:
  review:
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

### Python Script

```python
import requests

def auto_review_repo(repo_url, max_prs=5):
    """Automatically review multiple PRs"""
    response = requests.post(
        "http://localhost:8000/api/v1/batch",
        json={
            "repo_url": repo_url,
            "action": "review",
            "max_prs": max_prs
        }
    )
    return response.json()

# Usage
result = auto_review_repo("https://github.com/owner/repo")
print(f"Batch job: {result['batch_id']}")
```

## Troubleshooting

### "Connection refused"
```bash
# Check if server is running
curl http://localhost:8000/health

# If not running, start it
python -m pr_agent.servers.rest_api_server
```

### "GITHUB_TOKEN not found"
```bash
# Check environment
echo $GITHUB_TOKEN

# Set it
export GITHUB_TOKEN="your_token"

# Or use .env file
source venv/bin/activate
# Make sure .env is in the working directory
```

### "Invalid PR URL"
```bash
# Make sure URL format is correct
https://github.com/OWNER/REPO/pull/NUMBER

# Test with a real PR URL
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/facebook/react/pull/26000"
  }'
```

## Next Steps

1. **Customize** - Edit endpoints in `pr_agent/servers/rest_api_server.py`
2. **Deploy** - Follow `DEPLOYMENT_GUIDE.md` for production setup
3. **Integrate** - Connect with GitHub Actions, Slack, or your CI/CD
4. **Monitor** - Set up logging and metrics
5. **Secure** - Add authentication and rate limiting

## Resources

- [Full REST API Guide](./REST_API_SERVER_GUIDE.md)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [API Documentation](http://localhost:8000/docs) (when server is running)
- [PR Agent GitHub](https://github.com/Codium-ai/pr-agent)

---

**Questions?** Check the full documentation or open an issue on GitHub!
