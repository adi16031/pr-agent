# PR Agent REST API - Complete Setup Guide

Welcome! This guide will help you host PR Agent as a REST API service with multiple endpoints for PR review, description, improvements, issue detection, and more.

## 📋 What's Been Created

A complete, production-ready REST API server for PR Agent with:

✅ **REST API Endpoints** - Review, describe, improve, issues, ask, batch  
✅ **FastAPI Server** - With async support and interactive docs  
✅ **Docker Setup** - Docker & Docker Compose files included  
✅ **Python Client** - Pre-built client library with examples  
✅ **Comprehensive Docs** - Multiple guides for different use cases  
✅ **13 Deployment Options** - From local to Kubernetes  
✅ **Security Features** - Ready for production  
✅ **Monitoring Ready** - Logging and metrics support  

## 🚀 Quick Start (Choose Your Path)

### Path 1: I Want to Run It Locally RIGHT NOW ⚡
**Time: 5 minutes**

```bash
# Start with this
→ Read: QUICKSTART.md
```

Then:
```bash
chmod +x setup-rest-api.sh
./setup-rest-api.sh
export GITHUB_TOKEN="your_token"
export OPENAI_KEY="your_key"
python -m pr_agent.servers.rest_api_server
```

Open: http://localhost:8000/docs

---

### Path 2: I Want to Use Docker 🐳
**Time: 2 minutes**

```bash
# Start with this
→ Read: QUICKSTART.md (Docker section)
```

Then:
```bash
docker-compose up -d
# Server running at http://localhost:8000/docs
```

---

### Path 3: I Want Production Deployment 🏢
**Time: Varies by platform**

```bash
# Start with this
→ Read: DEPLOYMENT_GUIDE.md
```

Choose your platform:
- Heroku (5 min)
- AWS EC2 (15 min)
- AWS Lambda (15 min)
- DigitalOcean (5 min)
- Google Cloud Run (10 min)
- Kubernetes (30 min)
- And more...

---

### Path 4: I Want to Understand Everything 📚
**Time: 30 minutes**

1. **Start here**: `README_API_SERVER.md` - Overview
2. **API Reference**: `REST_API_SERVER_GUIDE.md` - All endpoints
3. **Architecture**: `ARCHITECTURE.md` - How it works
4. **Deployment**: `DEPLOYMENT_GUIDE.md` - Production setup
5. **Examples**: `examples/pr_agent_client.py` - Real code

---

## 📚 Documentation Map

### Essential Reading
| Document | Purpose | Read Time |
|----------|---------|-----------|
| **QUICKSTART.md** | Get running in 5 minutes | 5 min |
| **README_API_SERVER.md** | Complete overview | 10 min |
| **API_SETUP_SUMMARY.md** | What's been set up | 3 min |

### Reference
| Document | Purpose | Read Time |
|----------|---------|-----------|
| **REST_API_SERVER_GUIDE.md** | Complete API docs + examples | 30 min |
| **DEPLOYMENT_GUIDE.md** | 13 deployment options | 45 min |
| **ARCHITECTURE.md** | System design & data flow | 20 min |

### Code & Examples
| File | Purpose |
|------|---------|
| **pr_agent/servers/rest_api_server.py** | Main API server (FastAPI) |
| **examples/pr_agent_client.py** | Python client library |
| **PR_Agent_API.postman_collection.json** | Postman API collection |
| **.env.example** | Configuration template |

---

## 🎯 Common Use Cases

### "I just want to test the API locally"
```
1. Read: QUICKSTART.md
2. Run setup script
3. Update .env
4. Start server
5. Open http://localhost:8000/docs
6. Try endpoints in Swagger UI
```

### "I want to integrate with GitHub Actions"
```
1. Read: DEPLOYMENT_GUIDE.md (AWS EC2 section)
2. Deploy to EC2 or other cloud
3. Get public URL
4. Add webhook to GitHub Actions
5. See DEPLOYMENT_GUIDE.md Integration section
```

### "I want to process multiple PRs"
```
1. Read: REST_API_SERVER_GUIDE.md (Batch section)
2. Use POST /api/v1/batch endpoint
3. Or use Python client:
   from examples.pr_agent_client import PRAgentClient
   client.batch_process("repo_url", "review", max_prs=10)
```

### "I want to deploy to production"
```
1. Read: DEPLOYMENT_GUIDE.md
2. Choose platform (Heroku, AWS, DigitalOcean, etc)
3. Follow step-by-step instructions
4. Configure secrets/env vars
5. Deploy and test
```

### "I want to add authentication"
```
1. Read: DEPLOYMENT_GUIDE.md (Security section)
2. Edit rest_api_server.py to add API key check
3. Add @app.post("/api/v1/review", dependencies=[Depends(verify_key)])
4. Redeploy
```

---

## 🔧 File Structure

```
pr-agent/
├── QUICKSTART.md                    👈 Start here!
├── README_API_SERVER.md             👈 Then here
├── REST_API_SERVER_GUIDE.md         Complete API reference
├── DEPLOYMENT_GUIDE.md              All deployment options
├── ARCHITECTURE.md                  System design
├── API_SETUP_SUMMARY.md             What's been created
│
├── pr_agent/
│   └── servers/
│       └── rest_api_server.py       Main API server
│
├── docker/
│   └── Dockerfile.api               Docker image for API
│
├── examples/
│   └── pr_agent_client.py           Python client library
│
├── setup-rest-api.sh                Setup script
├── docker-compose.yml               Docker Compose config
├── .env.example                     Configuration template
│
└── PR_Agent_API.postman_collection.json  Postman requests
```

---

## 🎓 Learning Path

### Beginner (5-30 minutes)
1. **QUICKSTART.md** - Get it running
2. **Try the API** - Use Swagger UI at `/docs`
3. **Basic examples** - Curl commands in QUICKSTART.md

### Intermediate (1-2 hours)
1. **README_API_SERVER.md** - Understand the server
2. **REST_API_SERVER_GUIDE.md** - Learn all endpoints
3. **Python client examples** - Use examples/pr_agent_client.py
4. **Custom endpoints** - Modify for your needs

### Advanced (2-4 hours)
1. **ARCHITECTURE.md** - Understand design
2. **DEPLOYMENT_GUIDE.md** - Choose & deploy
3. **Production setup** - Add auth, rate limiting, monitoring
4. **Integration** - Connect to CI/CD, webhooks, etc

### Expert (4+ hours)
1. **Source code** - Modify rest_api_server.py
2. **Custom logic** - Add new endpoints
3. **Scaling** - Multi-instance, load balancing, Kubernetes
4. **Monitoring** - Prometheus, ELK stack, etc

---

## ✅ Verification Checklist

Before getting started, verify you have:

- [ ] Python 3.9+ installed
- [ ] Git installed
- [ ] GitHub account with token
- [ ] OpenAI account with API key (or other LLM)
- [ ] 5 GB disk space
- [ ] Internet connection

Check with:
```bash
python3 --version  # Should be 3.9+
git --version
echo $GITHUB_TOKEN  # Set?
echo $OPENAI_KEY    # Set?
```

---

## 🚀 Getting Started NOW

### Option A: 5-Minute Local Setup
```bash
# 1. Read the quick start
cat QUICKSTART.md

# 2. Run setup
chmod +x setup-rest-api.sh
./setup-rest-api.sh

# 3. Configure
nano .env  # Add GITHUB_TOKEN and OPENAI_KEY

# 4. Start
source venv/bin/activate
python -m pr_agent.servers.rest_api_server

# 5. Open browser
# http://localhost:8000/docs
```

### Option B: 2-Minute Docker Setup
```bash
# 1. Set environment
export GITHUB_TOKEN="your_token"
export OPENAI_KEY="your_key"

# 2. Start with Docker Compose
docker-compose up -d

# 3. Open browser
# http://localhost:8000/docs
```

### Option C: 1-Minute Verification
```bash
# See what's available
ls -la *.md               # Documentation files
ls -la docker/            # Docker files
ls -la pr_agent/servers/  # API server
ls -la examples/          # Examples
```

---

## 📊 What Each Endpoint Does

| Endpoint | What It Does | Use Case |
|----------|----------|----------|
| `/api/v1/review` | Comprehensive code review | Automated PR review |
| `/api/v1/describe` | Generate PR description | Auto-fill PR descriptions |
| `/api/v1/improve` | Code improvement suggestions | Find refactoring opportunities |
| `/api/v1/issues` | Detect potential issues | Find bugs before merge |
| `/api/v1/ask` | Ask questions about PR | Get answers on demand |
| `/api/v1/batch` | Process multiple PRs | Bulk operations |

---

## 💡 Pro Tips

1. **Use Swagger UI** - Visit `/docs` for interactive testing
2. **Check examples** - See `examples/pr_agent_client.py` for real code
3. **Use Postman** - Import `PR_Agent_API.postman_collection.json`
4. **Enable debug logs** - Set `LOG_LEVEL=DEBUG` for troubleshooting
5. **Save your setup** - Document your deployment for team
6. **Monitor usage** - Set up logging for production
7. **Back up config** - Keep `.env` file secure and backed up

---

## 🆘 Help & Support

### Something Not Working?

1. **Check Prerequisites**
   ```bash
   python3 --version  # 3.9+?
   pip list | grep fastapi  # Installed?
   echo $GITHUB_TOKEN  # Set?
   ```

2. **Check the Logs**
   ```bash
   # See detailed error messages
   export LOG_LEVEL=DEBUG
   python -m pr_agent.servers.rest_api_server
   ```

3. **Read the Guide**
   - Local issues? → QUICKSTART.md
   - API problems? → REST_API_SERVER_GUIDE.md
   - Deployment issues? → DEPLOYMENT_GUIDE.md
   - Architecture? → ARCHITECTURE.md

4. **Check Examples**
   ```bash
   python examples/pr_agent_client.py
   ```

5. **Search GitHub**
   - https://github.com/Codium-ai/pr-agent/issues

---

## 📞 Next Steps

**Choose what to do next:**

1. **Want to run it NOW?**
   → Go to **QUICKSTART.md**

2. **Want to understand it first?**
   → Read **README_API_SERVER.md**

3. **Want complete API docs?**
   → Read **REST_API_SERVER_GUIDE.md**

4. **Want to deploy to production?**
   → Read **DEPLOYMENT_GUIDE.md**

5. **Want to see architecture?**
   → Read **ARCHITECTURE.md**

6. **Want code examples?**
   → Check **examples/pr_agent_client.py**

---

## 🎉 Welcome!

You now have everything needed to:
- ✅ Run PR Agent locally
- ✅ Expose REST API endpoints
- ✅ Deploy to production
- ✅ Integrate with your workflow
- ✅ Scale as needed

**Let's get started! →** [QUICKSTART.md](./QUICKSTART.md)

---

**Last Updated:** December 9, 2025  
**Version:** 1.0.0  
**Status:** Ready for Production
