# PR Agent - Deployment & Hosting Guide

This guide covers different ways to host PR Agent as a REST API service with multiple endpoints.

## Quick Reference

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **Local/Development** | Simple, no setup | Limited access | Testing, development |
| **Docker** | Portable, isolated | Requires Docker | Development, staging |
| **Docker Compose** | Multi-service, easy | Requires Docker | Local development |
| **systemd (Linux)** | Native, persistent | Linux only | Production on Linux |
| **AWS Lambda** | Serverless, cheap | Cold starts | Low-traffic, event-driven |
| **AWS EC2** | Full control, scalable | More management | High-traffic, production |
| **Heroku** | Fast deployment, managed | Limited free tier | Quick prototypes |
| **DigitalOcean App Platform** | Simple, affordable | Limited customization | Startups, small teams |
| **Google Cloud Run** | Serverless, scalable | Pay per request | Bursty workloads |
| **Kubernetes** | Highly scalable, orchestrated | Complex setup | Enterprise, high-traffic |

---

## 1. Local Development

### Prerequisites
- Python 3.9+
- Git
- GitHub token
- OpenAI API key (or other LLM)

### Setup

```bash
# Clone repository
git clone https://github.com/Codium-ai/pr-agent.git
cd pr-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
pip install fastapi uvicorn

# Set credentials
export GITHUB_TOKEN="your_token"
export OPENAI_KEY="your_key"

# Run server
python -m pr_agent.servers.rest_api_server
```

Access at: http://localhost:8000/docs

---

## 2. Docker Deployment

### Build and Run

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

# View logs
docker logs -f pr-agent-api

# Stop container
docker stop pr-agent-api
```

### Push to Docker Registry

```bash
# Docker Hub
docker tag pr-agent-api:latest your-username/pr-agent-api:latest
docker push your-username/pr-agent-api:latest

# AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker tag pr-agent-api:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/pr-agent-api:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/pr-agent-api:latest
```

---

## 3. Docker Compose Deployment

```bash
# Create .env file
cat > .env << EOF
GITHUB_TOKEN=your_token
OPENAI_KEY=your_key
LOG_LEVEL=INFO
EOF

# Start services
docker-compose up -d

# View logs
docker-compose logs -f pr-agent-api

# Stop services
docker-compose down
```

---

## 4. Linux systemd Service

### Create Service File

```bash
sudo nano /etc/systemd/system/pr-agent.service
```

```ini
[Unit]
Description=PR Agent REST API
After=network.target

[Service]
Type=simple
User=pr-agent
WorkingDirectory=/home/pr-agent/pr-agent
Environment="GITHUB_TOKEN=your_token"
Environment="OPENAI_KEY=your_key"
Environment="LOG_LEVEL=INFO"
ExecStart=/home/pr-agent/pr-agent/venv/bin/python -m pr_agent.servers.rest_api_server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on startup
sudo systemctl enable pr-agent

# Start service
sudo systemctl start pr-agent

# Check status
sudo systemctl status pr-agent

# View logs
sudo journalctl -u pr-agent -f
```

---

## 5. AWS EC2 Deployment

### Step 1: Launch EC2 Instance

```bash
# Use AWS Console or CLI
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --count 1 \
  --instance-type t3.medium \
  --key-name my-key-pair \
  --security-groups default
```

### Step 2: Connect and Setup

```bash
# SSH into instance
ssh -i my-key-pair.pem ec2-user@instance-ip

# Update system
sudo yum update -y
sudo yum install -y python3 git

# Clone repository
cd /opt
sudo git clone https://github.com/Codium-ai/pr-agent.git
cd pr-agent

# Setup
sudo python3 -m venv venv
source venv/bin/activate
pip install -e .
pip install fastapi uvicorn
```

### Step 3: Create systemd Service

```bash
sudo nano /etc/systemd/system/pr-agent.service
```

[Use the systemd service file from Section 4]

### Step 4: Setup Reverse Proxy (Nginx)

```bash
sudo yum install -y nginx

sudo nano /etc/nginx/conf.d/pr-agent.conf
```

```nginx
upstream pr_agent {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://pr_agent;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://pr_agent;
        access_log off;
    }
}
```

```bash
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Step 5: Setup SSL with Let's Encrypt

```bash
sudo yum install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 6. AWS Lambda Deployment

### Create Lambda Function

```bash
# Create deployment package
pip install -r requirements.txt -t package/
cp -r pr_agent package/
cd package
zip -r ../lambda_function.zip .

# Upload to Lambda
aws lambda create-function \
  --function-name pr-agent-api \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT-ID:role/lambda-role \
  --handler app.lambda_handler \
  --zip-file fileb://../lambda_function.zip \
  --timeout 300 \
  --memory-size 512 \
  --environment "Variables={GITHUB_TOKEN=your_token,OPENAI_KEY=your_key}"
```

### Create Lambda Handler

```python
# app.py
from fastapi import FastAPI
from mangum import Mangum
from pr_agent.servers.rest_api_server import app

# Wrap FastAPI app for Lambda
lambda_handler = Mangum(app)
```

### Setup API Gateway

```bash
aws apigateway create-rest-api \
  --name pr-agent-api \
  --description "PR Agent REST API"
```

---

## 7. Heroku Deployment

### Step 1: Create Procfile

```bash
cat > Procfile << EOF
web: python -m pr_agent.servers.rest_api_server
EOF
```

### Step 2: Create runtime.txt

```
python-3.11.0
```

### Step 3: Deploy

```bash
# Login to Heroku
heroku login

# Create app
heroku create pr-agent-api

# Set environment variables
heroku config:set GITHUB_TOKEN="your_token"
heroku config:set OPENAI_KEY="your_key"

# Deploy
git push heroku main

# View logs
heroku logs -t

# Scale
heroku ps:scale web=1
```

Access at: https://pr-agent-api.herokuapp.com/docs

---

## 8. DigitalOcean App Platform

### Step 1: Create App Spec

```yaml
# app.yaml
name: pr-agent-api
services:
- name: pr-agent-api
  github:
    branch: main
    repo: your-username/pr-agent
  build_command: pip install -e . && pip install fastapi uvicorn
  run_command: python -m pr_agent.servers.rest_api_server
  envs:
  - key: GITHUB_TOKEN
    type: SECRET
    value: ${GITHUB_TOKEN}
  - key: OPENAI_KEY
    type: SECRET
    value: ${OPENAI_KEY}
  http_port: 8000
  health_check:
    http_path: /health
```

### Step 2: Deploy

```bash
doctl apps create --spec app.yaml
doctl apps list
doctl apps get <app-id>
```

---

## 9. Google Cloud Run

### Step 1: Prepare for Cloud Run

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
RUN pip install fastapi uvicorn
ENV PORT=8080
CMD ["python", "-m", "pr_agent.servers.rest_api_server"]
```

### Step 2: Build and Deploy

```bash
# Set project
gcloud config set project MY-PROJECT

# Build image
gcloud builds submit --tag gcr.io/MY-PROJECT/pr-agent-api

# Deploy
gcloud run deploy pr-agent-api \
  --image gcr.io/MY-PROJECT/pr-agent-api \
  --platform managed \
  --region us-central1 \
  --set-env-vars GITHUB_TOKEN="your_token",OPENAI_KEY="your_key" \
  --allow-unauthenticated
```

---

## 10. Kubernetes Deployment

### Step 1: Create Kubernetes Manifests

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pr-agent-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pr-agent-api
  template:
    metadata:
      labels:
        app: pr-agent-api
    spec:
      containers:
      - name: pr-agent-api
        image: your-registry/pr-agent-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: pr-agent-secrets
              key: github-token
        - name: OPENAI_KEY
          valueFrom:
            secretKeyRef:
              name: pr-agent-secrets
              key: openai-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: pr-agent-api
spec:
  selector:
    app: pr-agent-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Step 2: Deploy

```bash
# Create secrets
kubectl create secret generic pr-agent-secrets \
  --from-literal=github-token="your_token" \
  --from-literal=openai-key="your_key"

# Deploy
kubectl apply -f deployment.yaml

# Check status
kubectl get pods
kubectl get svc

# View logs
kubectl logs -l app=pr-agent-api -f
```

---

## 11. Monitoring & Logging

### Prometheus Metrics

```bash
pip install prometheus-client
```

```python
# Add to rest_api_server.py
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('pr_agent_requests_total', 'Total requests', ['method', 'endpoint'])
request_duration = Histogram('pr_agent_request_duration_seconds', 'Request duration')

@app.get("/metrics")
def metrics():
    return generate_latest()
```

### ELK Stack Logging

```bash
# Install Elasticsearch, Logstash, Kibana
docker-compose -f elk-compose.yml up -d

# Configure PR Agent logging
export LOGLEVEL=INFO
```

---

## 12. Security Best Practices

### 1. Use Environment Variables for Secrets

```bash
# Never hardcode credentials
export GITHUB_TOKEN="$(aws secretsmanager get-secret-value --secret-id github-token --query SecretString)"
export OPENAI_KEY="$(aws secretsmanager get-secret-value --secret-id openai-key --query SecretString)"
```

### 2. Add API Authentication

```python
from fastapi import Depends, HTTPException, Header

async def verify_api_key(x_token: str = Header()):
    if x_token != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_token

@app.post("/api/v1/review", dependencies=[Depends(verify_api_key)])
async def review_pr(request: PRReviewRequest):
    ...
```

### 3. Rate Limiting

```bash
pip install slowapi
```

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/v1/review")
@limiter.limit("10/minute")
async def review_pr(request: Request, pr_review: PRReviewRequest):
    ...
```

### 4. HTTPS/TLS

Use Let's Encrypt with Nginx or configure in your cloud provider.

---

## 13. Performance Optimization

### 1. Connection Pooling

```python
from sqlalchemy.pool import QueuePool

# For database connections
```

### 2. Caching

```bash
pip install redis
```

```python
from functools import lru_cache
import redis

cache = redis.Redis(host='localhost', port=6379)

@app.get("/api/v1/capabilities")
async def get_capabilities():
    cached = cache.get("capabilities")
    if cached:
        return json.loads(cached)
    ...
```

### 3. Load Balancing

Use Nginx, AWS ALB, or cloud provider load balancers.

---

## Quick Start Checklist

- [ ] Prerequisites installed (Python 3.9+, Git, credentials)
- [ ] Credentials configured (GITHUB_TOKEN, OPENAI_KEY)
- [ ] Dependencies installed (`pip install -e .`)
- [ ] Server starts without errors
- [ ] Health check passes (`/health`)
- [ ] Can access API docs (`/docs`)
- [ ] Tested with sample PR URL
- [ ] Setup monitoring/logging
- [ ] Configured SSL/HTTPS
- [ ] Implemented authentication
- [ ] Set up rate limiting
- [ ] Documented deployment process

---

## Troubleshooting

### Server won't start
```bash
# Check Python version
python3 --version  # Should be 3.9+

# Check dependencies
pip list | grep -i fastapi
pip install --upgrade fastapi uvicorn

# Check port availability
lsof -i :8000
```

### Credentials not found
```bash
# Verify environment variables
echo $GITHUB_TOKEN
echo $OPENAI_KEY

# Or check .env file
cat .env
```

### API returns 400 errors
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -m pr_agent.servers.rest_api_server

# Check server logs
tail -f logs/*.log
```

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [PR Agent Repository](https://github.com/Codium-ai/pr-agent)
