"""
PR Agent API Client Examples

This module provides client examples for interacting with the PR Agent REST API.
"""

import requests
import json
import time
from typing import Optional, Dict, Any
from urllib.parse import urljoin


class PRAgentClient:
    """Client for PR Agent REST API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the PR Agent client.
        
        Args:
            base_url: Base URL of the PR Agent server
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the server is healthy"""
        response = self.session.get(urljoin(self.base_url, "/health"))
        response.raise_for_status()
        return response.json()
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get available capabilities"""
        response = self.session.get(urljoin(self.base_url, "/api/v1/capabilities"))
        response.raise_for_status()
        return response.json()
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        response = self.session.get(urljoin(self.base_url, "/api/v1/config"))
        response.raise_for_status()
        return response.json()
    
    def review_pr(
        self,
        pr_url: str,
        extra_instructions: Optional[str] = None,
        ai_temperature: Optional[float] = None,
        async_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Review a pull request.
        
        Args:
            pr_url: URL of the pull request
            extra_instructions: Additional instructions for the review
            ai_temperature: Temperature setting for AI model
            async_mode: If True, returns immediately with job ID
        
        Returns:
            Response from the API
        """
        endpoint = "/api/v1/review/async" if async_mode else "/api/v1/review"
        payload = {"pr_url": pr_url}
        
        if extra_instructions:
            payload["extra_instructions"] = extra_instructions
        if ai_temperature is not None:
            payload["ai_temperature"] = ai_temperature
        
        response = self.session.post(
            urljoin(self.base_url, endpoint),
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def describe_pr(
        self,
        pr_url: str,
        extra_instructions: Optional[str] = None,
        async_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Generate description for a pull request.
        
        Args:
            pr_url: URL of the pull request
            extra_instructions: Additional instructions
            async_mode: If True, returns immediately with job ID
        
        Returns:
            Response from the API
        """
        endpoint = "/api/v1/describe/async" if async_mode else "/api/v1/describe"
        payload = {
            "pr_url": pr_url,
            "extra_instructions": extra_instructions or ""
        }
        
        response = self.session.post(
            urljoin(self.base_url, endpoint),
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def improve_code(
        self,
        pr_url: str,
        extra_instructions: Optional[str] = None,
        async_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Get code improvement suggestions.
        
        Args:
            pr_url: URL of the pull request
            extra_instructions: Additional instructions
            async_mode: If True, returns immediately with job ID
        
        Returns:
            Response from the API
        """
        endpoint = "/api/v1/improve/async" if async_mode else "/api/v1/improve"
        payload = {
            "pr_url": pr_url,
            "extra_instructions": extra_instructions or ""
        }
        
        response = self.session.post(
            urljoin(self.base_url, endpoint),
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def detect_issues(
        self,
        pr_url: str,
        severity: str = "all"
    ) -> Dict[str, Any]:
        """
        Detect issues in a pull request.
        
        Args:
            pr_url: URL of the pull request
            severity: Issue severity filter (all, critical, major, minor)
        
        Returns:
            Response from the API
        """
        payload = {
            "pr_url": pr_url,
            "severity": severity
        }
        
        response = self.session.post(
            urljoin(self.base_url, "/api/v1/issues"),
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def ask_question(
        self,
        pr_url: str,
        question: str
    ) -> Dict[str, Any]:
        """
        Ask a question about a pull request.
        
        Args:
            pr_url: URL of the pull request
            question: Question to ask
        
        Returns:
            Response from the API
        """
        payload = {
            "pr_url": pr_url,
            "question": question
        }
        
        response = self.session.post(
            urljoin(self.base_url, "/api/v1/ask"),
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def batch_process(
        self,
        repo_url: str,
        action: str,
        max_prs: int = 5,
        extra_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process multiple PRs in a repository.
        
        Args:
            repo_url: URL of the repository
            action: Action to perform (review, describe, improve, issues)
            max_prs: Maximum number of PRs to process
            extra_instructions: Additional instructions
        
        Returns:
            Response from the API
        """
        payload = {
            "repo_url": repo_url,
            "action": action,
            "max_prs": max_prs
        }
        
        if extra_instructions:
            payload["extra_instructions"] = extra_instructions
        
        response = self.session.post(
            urljoin(self.base_url, "/api/v1/batch"),
            json=payload
        )
        response.raise_for_status()
        return response.json()


def example_basic_review():
    """Example 1: Basic PR review"""
    print("Example 1: Basic PR Review")
    print("-" * 50)
    
    client = PRAgentClient()
    
    # Check server health
    health = client.health_check()
    print(f"Server Status: {health['status']}")
    
    # Review a PR
    result = client.review_pr(
        pr_url="https://github.com/owner/repo/pull/123"
    )
    print(f"Review Result: {json.dumps(result, indent=2)}")
    print()


def example_describe_with_instructions():
    """Example 2: PR description with custom instructions"""
    print("Example 2: PR Description with Custom Instructions")
    print("-" * 50)
    
    client = PRAgentClient()
    
    result = client.describe_pr(
        pr_url="https://github.com/owner/repo/pull/456",
        extra_instructions="Include API changes and backward compatibility notes"
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    print()


def example_improvement_suggestions():
    """Example 3: Code improvement suggestions"""
    print("Example 3: Code Improvement Suggestions")
    print("-" * 50)
    
    client = PRAgentClient()
    
    result = client.improve_code(
        pr_url="https://github.com/owner/repo/pull/789",
        extra_instructions="Focus on performance optimizations"
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    print()


def example_async_operations():
    """Example 4: Asynchronous operations"""
    print("Example 4: Asynchronous Operations")
    print("-" * 50)
    
    client = PRAgentClient()
    
    # Start async review
    result = client.review_pr(
        pr_url="https://github.com/owner/repo/pull/999",
        async_mode=True
    )
    print(f"Job ID: {result['job_id']}")
    print(f"Status: {result['status']}")
    print("Check back later for results...")
    print()


def example_batch_processing():
    """Example 5: Batch processing multiple PRs"""
    print("Example 5: Batch Processing")
    print("-" * 50)
    
    client = PRAgentClient()
    
    result = client.batch_process(
        repo_url="https://github.com/owner/repo",
        action="review",
        max_prs=10
    )
    print(f"Batch Job ID: {result['batch_id']}")
    print(f"PRs to process: {result['pr_count']}")
    print()


def example_ask_questions():
    """Example 6: Ask questions about PR"""
    print("Example 6: Ask Questions")
    print("-" * 50)
    
    client = PRAgentClient()
    
    questions = [
        "Is this backward compatible?",
        "What are the security implications?",
        "Should we add more test coverage?"
    ]
    
    for question in questions:
        result = client.ask_question(
            pr_url="https://github.com/owner/repo/pull/123",
            question=question
        )
        print(f"Q: {question}")
        print(f"Status: {result['status']}")
        print()


def example_detect_issues():
    """Example 7: Detect issues with severity filter"""
    print("Example 7: Detect Issues")
    print("-" * 50)
    
    client = PRAgentClient()
    
    # Detect critical issues only
    result = client.detect_issues(
        pr_url="https://github.com/owner/repo/pull/123",
        severity="critical"
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    print()


def example_full_workflow():
    """Example 8: Complete PR analysis workflow"""
    print("Example 8: Complete PR Analysis Workflow")
    print("-" * 50)
    
    client = PRAgentClient()
    pr_url = "https://github.com/owner/repo/pull/123"
    
    print("Starting comprehensive PR analysis...\n")
    
    # Step 1: Review
    print("Step 1: Code Review")
    review = client.review_pr(pr_url)
    print(f"✓ {review['message']}\n")
    
    # Step 2: Description
    print("Step 2: Generate Description")
    desc = client.describe_pr(pr_url)
    print(f"✓ {desc['message']}\n")
    
    # Step 3: Improvements
    print("Step 3: Get Improvement Suggestions")
    improve = client.improve_code(pr_url)
    print(f"✓ {improve['message']}\n")
    
    # Step 4: Issue Detection
    print("Step 4: Detect Issues")
    issues = client.detect_issues(pr_url, severity="critical")
    print(f"✓ {issues['message']}\n")
    
    print("Complete PR analysis finished!")


if __name__ == "__main__":
    """Run examples"""
    
    print("=" * 50)
    print("PR Agent API Client Examples")
    print("=" * 50)
    print()
    
    try:
        # Run examples (uncomment to execute)
        # example_basic_review()
        # example_describe_with_instructions()
        # example_improvement_suggestions()
        # example_async_operations()
        # example_batch_processing()
        # example_ask_questions()
        # example_detect_issues()
        # example_full_workflow()
        
        # For demonstration, just print available examples
        print("Available examples:")
        print("1. example_basic_review()")
        print("2. example_describe_with_instructions()")
        print("3. example_improvement_suggestions()")
        print("4. example_async_operations()")
        print("5. example_batch_processing()")
        print("6. example_ask_questions()")
        print("7. example_detect_issues()")
        print("8. example_full_workflow()")
        print()
        print("Note: Make sure PR Agent server is running!")
        print("Start it with: python -m pr_agent.servers.rest_api_server")
        print()
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to PR Agent server")
        print("Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"Error: {e}")
