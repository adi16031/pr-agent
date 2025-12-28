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
from urllib.parse import urlparse
from starlette_context import context
from starlette_context.middleware import RawContextMiddleware
from starlette.middleware import Middleware

from pr_agent.agent.pr_agent import PRAgent
from pr_agent.config_loader import get_settings, global_settings
from pr_agent.git_providers import get_git_provider
from pr_agent.log import LoggingFormat, get_logger, setup_logger

# Setup logging
setup_logger(fmt=LoggingFormat.JSON, level=get_settings().get("CONFIG.LOG_LEVEL", "INFO"))

CODE_AGENT_STORE_PATH = Path(__file__).resolve().parents[1] / "settings" / "code_agent_tokens.json"


def _mask_token(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    if len(token) <= 6:
        return "*" * len(token)
    return f"{token[:2]}***{token[-4:]}"


def _load_code_agent_store() -> dict:
    if not CODE_AGENT_STORE_PATH.is_file():
        return {"default": None, "repos": {}}
    try:
        data = json.loads(CODE_AGENT_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"default": None, "repos": {}}
    if not isinstance(data, dict):
        return {"default": None, "repos": {}}
    repos = data.get("repos") if isinstance(data.get("repos"), dict) else {}
    return {"default": data.get("default"), "repos": repos}


def _save_code_agent_store(data: dict) -> None:
    payload = {
        "default": data.get("default"),
        "repos": data.get("repos", {}),
    }
    CODE_AGENT_STORE_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True),
        encoding="utf-8"
    )


def _extract_repo_key(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    url = url.strip()
    if url.startswith("git@"):
        try:
            _, path = url.split(":", 1)
            if path.endswith(".git"):
                path = path[:-4]
            parts = path.split("/", 1)
            if len(parts) == 2:
                return f"{parts[0]}/{parts[1]}"
        except Exception:
            return None
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
    except Exception:
        return None
    if not path:
        return None
    parts = path.split("/")
    if "repos" in parts:
        idx = parts.index("repos")
        if len(parts) > idx + 2:
            return f"{parts[idx + 1]}/{parts[idx + 2]}"
    if len(parts) >= 2:
        repo = parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        return f"{parts[0]}/{repo}"
    return None


def _resolve_code_agent_token(pr_or_repo_url: Optional[str], request: Request) -> Optional[str]:
    header_token = request.headers.get("X-Code-Agent-Token")
    if header_token:
        return header_token
    store = _load_code_agent_store()
    repo_key = _extract_repo_key(pr_or_repo_url)
    if repo_key and repo_key in store.get("repos", {}):
        return store["repos"][repo_key]
    return store.get("default")


def _resolve_request_token(pr_or_repo_url: Optional[str], request: Request) -> Optional[str]:
    token = _resolve_code_agent_token(pr_or_repo_url, request)
    if token:
        return token
    return request.headers.get("X-GitHub-Token")


def _apply_request_token(pr_or_repo_url: Optional[str], request: Request) -> Optional[str]:
    token = _resolve_request_token(pr_or_repo_url, request)
    if token:
        get_settings().set("GITHUB.USER_TOKEN", token)
    return token


async def _run_with_token(pr_url: str, action: str, token: Optional[str]) -> None:
    if token:
        get_settings().set("GITHUB.USER_TOKEN", token)
    await pr_agent.handle_request(pr_url, action)


def init_request_context(request: Request) -> None:
    context["settings"] = copy.deepcopy(global_settings)
    context["git_provider"] = {}
    token = _resolve_request_token(None, request)
    if token:
        context["settings"].set("GITHUB.USER_TOKEN", token)


def _normalize_env_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return value.strip().strip('"').strip("'")


def _apply_openai_key_from_env() -> None:
    openai_key = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI.KEY")
    openai_key = _normalize_env_value(openai_key)
    if openai_key:
        get_settings().set("OPENAI.KEY", openai_key)
        if not openai_key.startswith("sk-"):
            get_logger().warning("OPENAI key does not start with 'sk-'; authentication may fail.")


def _apply_openai_api_base_from_env() -> None:
    openai_api_base = os.environ.get("OPENAI_API_BASE") or os.environ.get("OPENAI.API_BASE")
    openai_api_base = _normalize_env_value(openai_api_base)
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
    include_code_suggestions: Optional[bool] = True


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


class CodeAgentConfigRequest(BaseModel):
    token: str
    repo_url: Optional[str] = None
    set_default: Optional[bool] = False


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
async def review_pr(request: PRReviewRequest, background_tasks: BackgroundTasks, http_request: Request):
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
        _apply_request_token(request.pr_url, http_request)
        
        # Set extra instructions if provided
        if request.extra_instructions:
            settings = get_settings()
            settings.config.pr_reviewer.extra_instructions = request.extra_instructions
        
        # Set temperature if provided
        if request.ai_temperature is not None:
            settings = get_settings()
            settings.config.ai_temperature = request.ai_temperature
        
        # Execute review
        get_settings().data = {}
        await pr_agent.handle_request(request.pr_url, "review")
        review_output = get_settings().data.get("artifact")

        code_suggestions_output = None
        if request.include_code_suggestions:
            get_settings().data = {}
            await pr_agent.handle_request(request.pr_url, "improve")
            code_suggestions_output = get_settings().data.get("artifact")

        return {
            "status": "success",
            "message": "PR review completed",
            "pr_url": request.pr_url,
            "review": review_output,
            "code_suggestions": code_suggestions_output
        }
    except Exception as e:
        get_logger().error(f"Review failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/review/async", response_model=dict)
async def review_pr_async(request: PRReviewRequest, background_tasks: BackgroundTasks, http_request: Request):
    """
    Perform asynchronous PR review. Returns immediately with a job ID.
    
    Use /api/v1/review/status/{job_id} to check the status.
    """
    try:
        job_id = f"review_{request.pr_url.split('/')[-1]}"
        token = _apply_request_token(request.pr_url, http_request)
        get_logger().info(f"Starting async PR review with job_id: {job_id}")
        
        # Add background task
        background_tasks.add_task(
            _run_with_token,
            request.pr_url,
            "review",
            token
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
async def describe_pr(request: PRDescriptionRequest, http_request: Request):
    """
    Generate AI-powered description for a pull request.
    
    Analyzes code changes and generates a comprehensive description including:
    - Summary of changes
    - Files modified
    - Key functions/classes affected
    """
    try:
        get_logger().info(f"Starting PR description for {request.pr_url}")
        _apply_request_token(request.pr_url, http_request)
        
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
async def describe_pr_async(request: PRDescriptionRequest, background_tasks: BackgroundTasks, http_request: Request):
    """Asynchronous PR description generation"""
    try:
        job_id = f"describe_{request.pr_url.split('/')[-1]}"
        token = _apply_request_token(request.pr_url, http_request)
        get_logger().info(f"Starting async PR description with job_id: {job_id}")
        
        background_tasks.add_task(
            _run_with_token,
            request.pr_url,
            "describe",
            token
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
async def improve_code(request: PRImprovementsRequest, http_request: Request):
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
        _apply_request_token(request.pr_url, http_request)
        
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
async def improve_code_async(request: PRImprovementsRequest, background_tasks: BackgroundTasks, http_request: Request):
    """Asynchronous code improvement suggestions"""
    try:
        job_id = f"improve_{request.pr_url.split('/')[-1]}"
        token = _apply_request_token(request.pr_url, http_request)
        get_logger().info(f"Starting async code improvements with job_id: {job_id}")
        
        background_tasks.add_task(
            _run_with_token,
            request.pr_url,
            "improve",
            token
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
async def detect_issues(request: PRIssuesRequest, http_request: Request):
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
        _apply_request_token(request.pr_url, http_request)
        
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
async def ask_question(request: BaseModel, http_request: Request):
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
        _apply_request_token(pr_url, http_request)
        
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
async def batch_process_prs(request: BulkActionRequest, background_tasks: BackgroundTasks, http_request: Request):
    """
    Process multiple PRs at once for a repository.
    
    Actions: review, describe, improve, issues
    Returns immediately with batch job ID
    """
    try:
        get_logger().info(f"Starting batch {request.action} for {request.repo_url}")
        token = _apply_request_token(request.repo_url, http_request)
        
        # Get open PRs from repository
        provider = get_git_provider(request.repo_url)
        prs = provider.get_open_prs(limit=request.max_prs)
        
        batch_id = f"batch_{request.action}_{len(prs)}"
        
        for pr in prs:
            background_tasks.add_task(
                _run_with_token,
                pr.url,
                request.action,
                token
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


@app.post("/api/v1/code-agent/configure", response_model=dict)
async def configure_code_agent(request: CodeAgentConfigRequest):
    """Configure a code agent token for a repo or as default."""
    try:
        store = _load_code_agent_store()
        repo_key = _extract_repo_key(request.repo_url)
        if request.set_default or not repo_key:
            store["default"] = request.token
            scope = "default"
        else:
            store.setdefault("repos", {})[repo_key] = request.token
            scope = repo_key
        _save_code_agent_store(store)
        return {
            "status": "success",
            "scope": scope,
            "token": _mask_token(request.token)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/code-agent/config", response_model=dict)
async def get_code_agent_config(repo_url: Optional[str] = None):
    """Get current code agent configuration (tokens are masked)."""
    try:
        store = _load_code_agent_store()
        if repo_url:
            repo_key = _extract_repo_key(repo_url)
            return {
                "status": "success",
                "repo": repo_key,
                "token": _mask_token(store.get("repos", {}).get(repo_key))
            }
        masked_repos = {
            repo: _mask_token(token)
            for repo, token in store.get("repos", {}).items()
        }
        return {
            "status": "success",
            "default": _mask_token(store.get("default")),
            "repos": masked_repos
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/v1/code-agent/config", response_model=dict)
async def clear_code_agent_config(repo_url: Optional[str] = None, clear_default: Optional[bool] = False):
    """Clear code agent configuration for a repo or default."""
    try:
        store = _load_code_agent_store()
        repo_key = _extract_repo_key(repo_url)
        removed = False
        if repo_key and repo_key in store.get("repos", {}):
            store["repos"].pop(repo_key, None)
            removed = True
        if clear_default:
            store["default"] = None
            removed = True
        if removed:
            _save_code_agent_store(store)
        return {
            "status": "success",
            "repo": repo_key,
            "default_cleared": clear_default,
            "updated": removed
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
            },
            "code_agent": {
                "description": "Configure code agent tokens per repo",
                "endpoint": "/api/v1/code-agent/configure",
                "features": ["repo-scoped-token", "default-token", "masked-readback"]
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
