"""
Simple file-based cache for repository context.
Stores formatted repo context per repository full name and invalidates by TTL.
"""
import os
import json
import time
from typing import Optional

from pr_agent.log import get_logger
from pr_agent.config_loader import get_settings

DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".pr_agent_cache")
CACHE_SUBDIR = "repo_context"


def _get_cache_dir() -> str:
    base = get_settings().get("config.repo_context_cache_dir", DEFAULT_CACHE_DIR)
    path = os.path.join(base, CACHE_SUBDIR)
    os.makedirs(path, exist_ok=True)
    return path


def _cache_file_for_repo(repo_full_name: str) -> str:
    safe = repo_full_name.replace("/", "__")
    return os.path.join(_get_cache_dir(), f"{safe}.json")


def get_cached_context(repo_full_name: str) -> Optional[str]:
    try:
        if not get_settings().get("config.enable_repo_context_cache", True):
            return None
        cache_file = _cache_file_for_repo(repo_full_name)
        if not os.path.exists(cache_file):
            return None
        with open(cache_file, "r") as f:
            data = json.load(f)
        ttl_hours = float(get_settings().get("config.repo_context_cache_ttl_hours", 24))
        if ttl_hours <= 0:
            return None
        expires_at = data.get("ts", 0) + int(ttl_hours * 3600)
        if time.time() > expires_at:
            try:
                os.remove(cache_file)
            except Exception:
                pass
            return None
        return data.get("context", "") or None
    except Exception as e:
        get_logger().debug(f"repo context cache read failed: {e}")
        return None


def set_cached_context(repo_full_name: str, context: str) -> None:
    try:
        if not get_settings().get("config.enable_repo_context_cache", True):
            return
        cache_file = _cache_file_for_repo(repo_full_name)
        payload = {"repo": repo_full_name, "context": context, "ts": int(time.time())}
        with open(cache_file, "w") as f:
            json.dump(payload, f)
    except Exception as e:
        get_logger().debug(f"repo context cache write failed: {e}")
