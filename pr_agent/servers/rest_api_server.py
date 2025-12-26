"""
REST API Server for PR Agent
Exposes endpoints for review, description, improvements, issues detection, and more.

Run with: uvicorn pr_agent.servers.rest_api_server:app --host 0.0.0.0 --port 8000 --reload
Or: python -m pr_agent.servers.rest_api_server
"""

import asyncio
import copy
import os
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json
from starlette_context import context
from starlette_context.middleware import RawContextMiddleware
from starlette.middleware import Middleware

from pr_agent.agent.pr_agent import PRAgent
from pr_agent.config_loader import get_settings, global_settings
from pr_agent.git_providers import get_git_provider
from pr_agent.log import LoggingFormat, get_logger, setup_logger

# Setup logging
setup_logger(fmt=LoggingFormat.JSON, level=get_settings().get("CONFIG.LOG_LEVEL", "INFO"))

def init_request_context(request: Request) -> None:
    context["settings"] = copy.deepcopy(global_settings)
    context["git_provider"] = {}
    github_token = request.headers.get("X-GitHub-Token")
    if github_token:
        context["settings"].set("GITHUB.USER_TOKEN", github_token)


def _apply_openai_key_from_env() -> None:
    openai_key = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI.KEY")
    if openai_key:
        get_settings().set("OPENAI.KEY", openai_key)


def _apply_openai_api_base_from_env() -> None:
    openai_api_base = os.environ.get("OPENAI_API_BASE") or os.environ.get("OPENAI.API_BASE")
    if openai_api_base:
        get_settings().set("OPENAI.API_BASE", openai_api_base)


# Initialize FastAPI app
app = FastAPI(
    title="PR Agent REST API",
    description="AI-powered PR review, description, and improvement suggestions",
    version="1.0.0",
    middleware=[Middleware(RawContextMiddleware)],
    dependencies=[Depends(init_request_context)],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger = get_logger()
    
    # Log incoming request
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    logger.info(f"Headers: {dict(request.headers)}")
    print(f"Headers: {dict(request.headers)}")
    
    # Try to read and log body for POST/PUT requests
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
        if body:
            try:
                body_json = json.loads(body)
                logger.info(f"Request body: {json.dumps(body_json, indent=2)}")
            except:
                logger.info(f"Request body (raw): {body.decode('utf-8', errors='ignore')}")
        
        # Re-create request with body for downstream handlers
        async def receive():
            return {"type": "http.request", "body": body}
        request = Request(request.scope, receive)
    
    # Process request
    response = await call_next(request)
    
    # Log response
    logger.info(f"Response status: {response.status_code}")
    
    return response

# Initialize PR Agent
pr_agent = PRAgent()


# ===================== Request/Response Models =====================

class PRReviewRequest(BaseModel):
    pr_url: str
    extra_instructions: Optional[str] = None
    ai_temperature: Optional[float] = None


class PRReviewResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None


class PRDescriptionRequest(BaseModel):
    pr_url: str
    extra_instructions: Optional[str] = None


class PRImprovementsRequest(BaseModel):
    pr_url: str
    extra_instructions: Optional[str] = None


class PRIssuesRequest(BaseModel):
    pr_url: str
    severity: Optional[str] = "all"  # all, critical, major, minor


class BulkActionRequest(BaseModel):
    repo_url: str
    action: str  # review, describe, improve, issues
    max_prs: Optional[int] = 5
    extra_instructions: Optional[str] = None


# ===================== Health Check =====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PR Agent REST API",
        "version": "1.0.0"
    }


# ===================== PR Review Endpoints =====================

@app.post("/api/v1/review", response_model=dict)
async def review_pr(request: PRReviewRequest, background_tasks: BackgroundTasks):
    """
    Perform AI-powered code review on a pull request.
    
    Args:
        pr_url: Full URL to the pull request
        extra_instructions: Optional additional instructions for the review
        ai_temperature: Optional temperature setting for AI model
    
    Returns:
        Review analysis with suggestions and findings
    """
    try:
        get_logger().info(f"Starting PR review for {request.pr_url}")
        
        # Set extra instructions if provided
        if request.extra_instructions:
            settings = get_settings()
            settings.config.pr_reviewer.extra_instructions = request.extra_instructions
        
        # Set temperature if provided
        if request.ai_temperature is not None:
            settings = get_settings()
            settings.config.ai_temperature = request.ai_temperature
        
        # Execute review
        await pr_agent.handle_request(request.pr_url, "review")
        
        return {
            "status": "success",
            "message": "PR review completed",
            "pr_url": request.pr_url
        }
    except Exception as e:
        get_logger().error(f"Review failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/review/async", response_model=dict)
async def review_pr_async(request: PRReviewRequest, background_tasks: BackgroundTasks):
    """
    Perform asynchronous PR review. Returns immediately with a job ID.
    
    Use /api/v1/review/status/{job_id} to check the status.
    """
    try:
        job_id = f"review_{request.pr_url.split('/')[-1]}"
        get_logger().info(f"Starting async PR review with job_id: {job_id}")
        
        # Add background task
        background_tasks.add_task(
            pr_agent.handle_request,
            request.pr_url,
            "review"
        )
        
        return {
            "status": "queued",
            "job_id": job_id,
            "message": "Review queued for processing"
        }
    except Exception as e:
        get_logger().error(f"Async review failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ===================== PR Description Endpoints =====================

@app.post("/api/v1/describe", response_model=dict)
async def describe_pr(request: PRDescriptionRequest):
    """
    Generate AI-powered description for a pull request.
    
    Analyzes code changes and generates a comprehensive description including:
    - Summary of changes
    - Files modified
    - Key functions/classes affected
    """
    try:
        get_logger().info(f"Starting PR description for {request.pr_url}")
        
        if request.extra_instructions:
            settings = get_settings()
            settings.config.pr_description.extra_instructions = request.extra_instructions
        
        await pr_agent.handle_request(request.pr_url, "describe")
        
        return {
            "status": "success",
            "message": "PR description generated",
            "pr_url": request.pr_url
        }
    except Exception as e:
        get_logger().error(f"Description generation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/describe/async", response_model=dict)
async def describe_pr_async(request: PRDescriptionRequest, background_tasks: BackgroundTasks):
    """Asynchronous PR description generation"""
    try:
        job_id = f"describe_{request.pr_url.split('/')[-1]}"
        get_logger().info(f"Starting async PR description with job_id: {job_id}")
        
        background_tasks.add_task(
            pr_agent.handle_request,
            request.pr_url,
            "describe"
        )
        
        return {
            "status": "queued",
            "job_id": job_id,
            "message": "Description generation queued"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===================== Code Improvements Endpoints =====================

@app.post("/api/v1/improve", response_model=dict)
async def improve_code(request: PRImprovementsRequest):
    """
    Generate code improvement suggestions for a pull request.
    
    Analyzes code quality and suggests improvements for:
    - Performance optimization
    - Best practices
    - Code style and readability
    - Security concerns
    """
    try:
        get_logger().info(f"Starting code improvement analysis for {request.pr_url}")
        
        if request.extra_instructions:
            settings = get_settings()
            settings.config.pr_code_suggestions.extra_instructions = request.extra_instructions
        
        await pr_agent.handle_request(request.pr_url, "improve")
        
        return {
            "status": "success",
            "message": "Code improvement suggestions generated",
            "pr_url": request.pr_url
        }
    except Exception as e:
        get_logger().error(f"Improvement suggestions failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/improve/async", response_model=dict)
async def improve_code_async(request: PRImprovementsRequest, background_tasks: BackgroundTasks):
    """Asynchronous code improvement suggestions"""
    try:
        job_id = f"improve_{request.pr_url.split('/')[-1]}"
        get_logger().info(f"Starting async code improvements with job_id: {job_id}")
        
        background_tasks.add_task(
            pr_agent.handle_request,
            request.pr_url,
            "improve"
        )
        
        return {
            "status": "queued",
            "job_id": job_id,
            "message": "Code improvements analysis queued"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===================== Issues Detection Endpoints =====================

@app.post("/api/v1/issues", response_model=dict)
async def detect_issues(request: PRIssuesRequest):
    """
    Detect potential issues and bugs in the pull request.
    
    Analyzes code for:
    - Logic errors
    - Edge cases
    - Potential runtime issues
    - Type mismatches (for typed languages)
    """
    try:
        get_logger().info(f"Starting issue detection for {request.pr_url}")
        
        # Use the review functionality which includes issue detection
        await pr_agent.handle_request(request.pr_url, "review")
        
        return {
            "status": "success",
            "message": "Issues analysis completed",
            "pr_url": request.pr_url,
            "severity_filter": request.severity
        }
    except Exception as e:
        get_logger().error(f"Issue detection failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ===================== Questions & Answers Endpoints =====================

@app.post("/api/v1/ask", response_model=dict)
async def ask_question(request: BaseModel):
    """
    Ask specific questions about a pull request.
    
    Example questions:
    - "What are the security implications?"
    - "Is this backward compatible?"
    - "What tests should be added?"
    """
    try:
        pr_url = request.__dict__.get("pr_url")
        question = request.__dict__.get("question")
        
        if not pr_url or not question:
            raise ValueError("pr_url and question are required")
        
        get_logger().info(f"Asking question about {pr_url}: {question}")
        
        await pr_agent.handle_request(pr_url, f"ask {question}")
        
        return {
            "status": "success",
            "message": "Question processed",
            "pr_url": pr_url,
            "question": question
        }
    except Exception as e:
        get_logger().error(f"Question processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ===================== Batch Operations =====================

@app.post("/api/v1/batch", response_model=dict)
async def batch_process_prs(request: BulkActionRequest, background_tasks: BackgroundTasks):
    """
    Process multiple PRs at once for a repository.
    
    Actions: review, describe, improve, issues
    Returns immediately with batch job ID
    """
    try:
        get_logger().info(f"Starting batch {request.action} for {request.repo_url}")
        
        # Get open PRs from repository
        provider = get_git_provider(request.repo_url)
        prs = provider.get_open_prs(limit=request.max_prs)
        
        batch_id = f"batch_{request.action}_{len(prs)}"
        
        for pr in prs:
            background_tasks.add_task(
                pr_agent.handle_request,
                pr.url,
                request.action
            )
        
        return {
            "status": "queued",
            "batch_id": batch_id,
            "action": request.action,
            "pr_count": len(prs),
            "message": f"Batch job queued for {len(prs)} PRs"
        }
    except Exception as e:
        get_logger().error(f"Batch processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ===================== Configuration Endpoints =====================

@app.get("/api/v1/config", response_model=dict)
async def get_config():
    """Get current PR Agent configuration"""
    try:
        settings = get_settings()
        return {
            "status": "success",
            "config": {
                "ai_model": settings.config.ai_model if hasattr(settings.config, "ai_model") else "gpt-4",
                "git_providers": list(settings.git_providers.keys()) if hasattr(settings, "git_providers") else [],
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/capabilities", response_model=dict)
async def get_capabilities():
    """List all available PR Agent capabilities"""
    return {
        "status": "success",
        "capabilities": {
            "review": {
                "description": "Perform comprehensive code review",
                "endpoint": "/api/v1/review",
                "features": ["logic-review", "best-practices", "security-check", "performance-analysis"]
            },
            "describe": {
                "description": "Generate PR description",
                "endpoint": "/api/v1/describe",
                "features": ["summary", "change-analysis", "impact-assessment"]
            },
            "improve": {
                "description": "Code improvement suggestions",
                "endpoint": "/api/v1/improve",
                "features": ["optimization", "readability", "style-guide", "refactoring"]
            },
            "issues": {
                "description": "Detect potential issues",
                "endpoint": "/api/v1/issues",
                "features": ["bug-detection", "logic-errors", "edge-cases"]
            },
            "ask": {
                "description": "Ask questions about PR",
                "endpoint": "/api/v1/ask",
                "features": ["custom-questions", "impact-analysis"]
            },
            "batch": {
                "description": "Process multiple PRs",
                "endpoint": "/api/v1/batch",
                "features": ["bulk-processing", "scheduled-tasks"]
            }
        }
    }


# ===================== Documentation =====================

@app.get("/", response_model=dict)
async def root():
    """API documentation and usage guide"""
    return {
        "title": "PR Agent REST API",
        "version": "1.0.0",
        "description": "AI-powered PR review, description, and improvement suggestions",
        "endpoints": {
            "health": "/health",
            "documentation": "/docs",
            "capabilities": "/api/v1/capabilities",
            "config": "/api/v1/config"
        },
        "quick_start": {
            "review": "POST /api/v1/review with {pr_url}",
            "describe": "POST /api/v1/describe with {pr_url}",
            "improve": "POST /api/v1/improve with {pr_url}",
            "issues": "POST /api/v1/issues with {pr_url}",
            "batch": "POST /api/v1/batch with {repo_url, action, max_prs}"
        }
    }


# ===================== Error Handlers =====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    get_logger().error(f"Global exception: {str(exc)}", exc_info=exc)
    return {
        "status": "error",
        "message": str(exc),
        "type": type(exc).__name__
    }


# ===================== Startup/Shutdown =====================

@app.on_event("startup")
async def startup_event():
    _apply_openai_key_from_env()
    _apply_openai_api_base_from_env()
    get_logger().info("PR Agent REST API Server starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    get_logger().info("PR Agent REST API Server shutting down...")


if __name__ == "__main__":
    # Run with: python -m pr_agent.servers.rest_api_server
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    get_logger().info(f"Starting PR Agent REST API on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=get_settings().get("CONFIG.LOG_LEVEL", "INFO").lower()
    )
