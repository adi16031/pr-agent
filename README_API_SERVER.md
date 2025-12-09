# PR Agent REST API Server

Transform PR Agent into a scalable REST API service with endpoints for PR review, description generation, code improvements, issue detection, and more.

## 🎯 Overview

This setup provides a **production-ready REST API** for PR Agent with:

- ✅ **Multiple endpoints** - Review, describe, improve, issues, ask, batch
- ✅ **Async support** - Non-blocking long-running operations  
- ✅ **Interactive docs** - Swagger UI included
- ✅ **Docker ready** - Run anywhere with Docker/Compose
- ✅ **Python client** - Pre-built library with examples
- ✅ **13 deployment options** - From local to Kubernetes
- ✅ **Production features** - Rate limiting, monitoring, security
- ✅ **Fully documented** - Guides, examples, and troubleshooting

## 🚀 Get Started in 5 Minutes

### Quick Start

```bash
# 1. Run setup script
chmod +x setup-rest-api.sh
./setup-rest-api.sh

# 2. Update .env with credentials
export GITHUB_TOKEN="your_token"
export OPENAI_KEY="your_key"

# 3. Start server
source venv/bin/activate
python -m pr_agent.servers.rest_api_server

# 4. Open browser
# http://localhost:8000/docs
```

### Or with Docker

```bash
docker-compose up -d
# Server running at http://localhost:8000/docs
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **`QUICKSTART.md`** | 5-minute setup guide |
| **`REST_API_SERVER_GUIDE.md`** | Complete API reference & usage |
| **`DEPLOYMENT_GUIDE.md`** | 13 deployment options |
| **`API_SETUP_SUMMARY.md`** | Setup overview & summary |
| **`examples/pr_agent_client.py`** | Python client library |
| **`PR_Agent_API.postman_collection.json`** | Postman API collection |

## 🔧 API Endpoints

### Core Endpoints

```
POST /api/v1/review         - Comprehensive code review
POST /api/v1/describe       - Generate PR description  
POST /api/v1/improve        - Code improvement suggestions
POST /api/v1/issues         - Detect potential issues
POST /api/v1/ask            - Ask questions about PR
POST /api/v1/batch          - Process multiple PRs
```

### Async Variants

```
POST /api/v1/review/async   - Start review (non-blocking)
POST /api/v1/describe/async - Start description (non-blocking)
POST /api/v1/improve/async  - Start improvements (non-blocking)
```

### Info Endpoints

```
GET  /health                 - Health check
GET  /docs                   - Interactive API documentation
GET  /api/v1/capabilities   - List available features
GET  /api/v1/config         - Current configuration
```

## 💡 Usage Examples

### 1. Review a PR

```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/123"}'
```

### 2. Generate Description

```bash
curl -X POST http://localhost:8000/api/v1/describe \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123",
    "extra_instructions": "Include API changes"
  }'
```

### 3. Get Improvements

```bash
curl -X POST http://localhost:8000/api/v1/improve \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123",
    "extra_instructions": "Focus on performance"
  }'
```

### 4. Detect Issues

```bash
curl -X POST http://localhost:8000/api/v1/issues \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123",
    "severity": "critical"
  }'
```

### 5. Python Client

```python
from examples.pr_agent_client import PRAgentClient

client = PRAgentClient()

# Review PR
review = client.review_pr("https://github.com/owner/repo/pull/123")

# Describe PR
desc = client.describe_pr("https://github.com/owner/repo/pull/123")

# Get improvements
improve = client.improve_code("https://github.com/owner/repo/pull/123")

# Detect issues
issues = client.detect_issues("https://github.com/owner/repo/pull/123")

# Ask questions
answer = client.ask_question(
    "https://github.com/owner/repo/pull/123",
    "Is this backward compatible?"
)

# Batch process
batch = client.batch_process(
    "https://github.com/owner/repo",
    action="review",
    max_prs=10
)
```

## 🌐 Deployment Options

| Platform | Time | Cost | Difficulty |
|----------|------|------|-----------|
| **Local/Dev** | 5 min | Free | ⭐ |
| **Docker** | 2 min | Free | ⭐ |
| **Docker Compose** | 5 min | Free | ⭐ |
| **systemd (Linux)** | 10 min | Free | ⭐⭐ |
| **Heroku** | 5 min | $7-50/mo | ⭐⭐ |
| **AWS EC2** | 15 min | $10-100/mo | ⭐⭐⭐ |
| **AWS Lambda** | 15 min | Pay/use | ⭐⭐⭐ |
| **DigitalOcean** | 5 min | $12/mo | ⭐⭐ |
| **Google Cloud Run** | 10 min | Pay/use | ⭐⭐ |
| **Kubernetes** | 30 min | Variable | ⭐⭐⭐⭐ |

**👉 See `DEPLOYMENT_GUIDE.md` for step-by-step instructions for each platform.**

## ⚙️ Configuration

### Environment Variables

```bash
# Required
GITHUB_TOKEN=ghp_your_token_here
OPENAI_KEY=sk_your_key_here

# Optional
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
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

See `.env.example` for full configuration options.

## 🐳 Docker Usage

### Build Image

```bash
docker build -t pr-agent-api:latest -f docker/Dockerfile.api .
```

### Run Container

```bash
docker run -d \
  -p 8000:8000 \
  -e GITHUB_TOKEN="your_token" \
  -e OPENAI_KEY="your_key" \
  --name pr-agent-api \
  pr-agent-api:latest
```

### Docker Compose

```bash
docker-compose up -d
docker-compose logs -f pr-agent-api
docker-compose down
```

## 📊 Files & Structure

```
pr_agent/
├── servers/
│   └── rest_api_server.py          # Main API server
├── QUICKSTART.md                   # 5-minute setup
├── REST_API_SERVER_GUIDE.md        # Complete reference
├── DEPLOYMENT_GUIDE.md             # 13 deployment options
├── API_SETUP_SUMMARY.md            # Setup summary
├── .env.example                    # Configuration template
├── setup-rest-api.sh               # Setup script
├── docker-compose.yml              # Docker Compose config
├── docker/
│   └── Dockerfile.api              # API Docker image
└── examples/
    └── pr_agent_client.py          # Python client library
```

## 🔐 Security

For production deployment:

1. **Add authentication**
   ```python
   @app.post("/api/v1/review")
   async def review_pr(request: Request, data: dict):
       verify_api_key(request.headers.get("X-API-Key"))
   ```

2. **Enable rate limiting**
   ```python
   from slowapi import Limiter
   limiter.limit("10/minute")
   ```

3. **Configure HTTPS/TLS** - Use Let's Encrypt with Nginx

4. **Use environment secrets** - Never hardcode credentials

5. **Implement CORS** - Already configured in server

See `DEPLOYMENT_GUIDE.md` Security section for details.

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### Get Capabilities
```bash
curl http://localhost:8000/api/v1/capabilities
```

### Try with Real PR
```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/facebook/react/pull/26000"}'
```

## 📈 Performance & Scaling

### Single Instance
- Development and testing
- Small teams
- ~100-1000 requests/day

### Multiple Instances
- Production use
- Medium teams
- Use load balancer (Nginx, AWS ALB)
- ~1000-10000 requests/day

### Kubernetes
- Large scale
- Enterprise
- Auto-scaling
- 10000+ requests/day

See `DEPLOYMENT_GUIDE.md` for scaling strategies.

## 🔗 Integrations

### GitHub Actions

```yaml
name: PR Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Review
        run: |
          curl -X POST https://your-pr-agent/api/v1/review \
            -d '{"pr_url": "${{ github.event.pull_request.html_url }}"}'
```

### GitLab CI

```yaml
pr_review:
  script:
    - curl -X POST https://your-pr-agent/api/v1/review \
        -d '{"pr_url": "$CI_MERGE_REQUEST_PROJECT_URL/-/merge_requests/$CI_MERGE_REQUEST_IID"}'
```

### Slack Bot

```python
# Post results to Slack
slack_client.post_message(
    channel="#reviews",
    text=f"PR Review: {result['status']}"
)
```

## 📞 Support & Help

- **Quick Start**: See `QUICKSTART.md`
- **Full Documentation**: See `REST_API_SERVER_GUIDE.md`
- **Deployment**: See `DEPLOYMENT_GUIDE.md`
- **API Docs**: http://localhost:8000/docs (when running)
- **Examples**: `examples/pr_agent_client.py`
- **Issues**: https://github.com/Codium-ai/pr-agent/issues

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Docker Documentation](https://docs.docker.com/)
- [REST API Best Practices](https://restfulapi.net/)
- [PR Agent GitHub](https://github.com/Codium-ai/pr-agent)

## 📋 Checklist

- [ ] Prerequisites installed (Python 3.9+, Git)
- [ ] GitHub token obtained and configured
- [ ] OpenAI (or other LLM) API key obtained
- [ ] Dependencies installed (`pip install -e .`)
- [ ] Server starts without errors
- [ ] Health check passes (`/health`)
- [ ] API docs accessible (`/docs`)
- [ ] Tested with sample PR URL
- [ ] Deployment method chosen
- [ ] Production setup completed
- [ ] Monitoring configured
- [ ] Team trained on API usage

## 🚀 Next Steps

1. **Start with QUICKSTART.md** - Get running in 5 minutes
2. **Explore API docs** - Visit `/docs` when server is running
3. **Try examples** - Use provided examples to understand API
4. **Choose deployment** - Pick platform from DEPLOYMENT_GUIDE.md
5. **Deploy to production** - Follow deployment instructions
6. **Integrate with CI/CD** - Connect to your workflow
7. **Monitor & maintain** - Set up logging and alerts

---

**Ready to get started? See [`QUICKSTART.md`](./QUICKSTART.md) for immediate setup instructions.**
