from flask import Flask, jsonify, render_template, request, Response, redirect, url_for, session
from pathlib import Path
from datetime import datetime
import subprocess
import json
import os
import secrets
import shutil
import base64
import textwrap

# GitPython
from git import Repo, InvalidGitRepositoryError

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# GitHub OAuth configuration
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET', '')


def find_repo_root(start: Path) -> Path:
    root = start.resolve()
    while root != root.parent:
        if (root / '.git').exists():
            return root
        root = root.parent
    return start.resolve()


def get_repo_info(path: Path):
    repo = {}
    repo['name'] = path.name
    repo['path'] = str(path)
    try:
        r = Repo(path)
        remotes = []
        for remote in r.remotes:
            for url in remote.urls:
                remotes.append(f"{remote.name}\t{url}")
        repo['remotes'] = remotes

        branches = [b.name for b in r.branches]
        # add remote heads names
        branches += [h.name for h in r.remotes]
        repo['branches'] = branches

        commit = r.head.commit
        repo['last_commit'] = f"{commit.hexsha[:7]} - {commit.message.splitlines()[0]} ({commit.committed_datetime.isoformat()}) <{commit.author.name}>"

        files = [p.name for p in path.iterdir() if p.is_file()]
        repo['files'] = files
    except InvalidGitRepositoryError:
        repo['remotes'] = []
        repo['branches'] = []
        repo['last_commit'] = ''
        repo['files'] = [p.name for p in path.iterdir() if p.is_file()]
    except Exception as e:
        repo['remotes'] = [str(e)]
        repo['branches'] = []
        repo['last_commit'] = ''
        repo['files'] = []
    return repo


def _parse_github_remote_url(url: str):
    # support formats: git@github.com:owner/repo.git or https://github.com/owner/repo.git
    try:
        if url.startswith('git@'):
            # git@github.com:owner/repo.git
            _, path = url.split(':', 1)
            owner_repo = path
            if owner_repo.endswith('.git'):
                owner_repo = owner_repo[:-4]
            owner, repo = owner_repo.split('/', 1)
            return owner, repo

        # handle https:// or http://
        if url.startswith('http'):
            # strip possible trailing .git
            if url.endswith('.git'):
                url = url[:-4]
            parts = url.rstrip('/').split('/')
            # expect .../owner/repo
            if len(parts) >= 2:
                owner = parts[-2]
                repo = parts[-1]
                return owner, repo
    except Exception:
        return None, None
    return None, None


def get_open_prs(path: Path):
    # Determine owner/repo from remotes (prefer origin)
    try:
        r = Repo(path)
        origin = None
        for remote in r.remotes:
            if remote.name == 'origin':
                origin = next(iter(remote.urls), None)
                break
        if origin is None and r.remotes:
            origin = next(iter(r.remotes[0].urls), None)
    except Exception:
        origin = None

    if not origin:
        return {'error': 'no git remote found', 'prs': []}

    owner, repo = _parse_github_remote_url(origin)
    if not owner or not repo:
        return {'error': 'unable to parse remote url', 'prs': []}

    # Get token via helper (env or pr_agent/settings/.secrets.toml in repo)
    gh_token = _get_github_token()
    headers = {'Accept': 'application/vnd.github+json'}
    if gh_token:
        headers['Authorization'] = f'token {gh_token}'

    import requests
    api = f'https://api.github.com/repos/{owner}/{repo}/pulls?state=open'
    try:
        r = requests.get(api, headers=headers, timeout=10)
        if r.status_code != 200:
            # include response text to aid debugging (e.g., 404 for wrong owner/repo)
            text = r.text
            return {'error': f'GitHub API status {r.status_code}: {text}', 'prs': []}
        items = r.json()
        prs = []
        for it in items:
            prs.append({
                'number': it.get('number'),
                'title': it.get('title'),
                'user': it.get('user', {}).get('login'),
                'html_url': it.get('html_url'),
                'created_at': it.get('created_at')
            })
        return {'error': None, 'prs': prs}
    except Exception as e:
        return {'error': str(e), 'prs': []}


def _get_github_token():
    import os
    gh_token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if gh_token:
        return gh_token
    # fallback to local secrets file located relative to the repository root
    try:
        import toml
        repo_root = find_repo_root(Path.cwd())
        sec_path = repo_root / 'pr_agent' / 'settings' / '.secrets.toml'
        if sec_path.is_file():
            data = toml.load(sec_path)
            gh = data.get('github') or {}
            gh_token = gh.get('user_token') or gh.get('user-token') or gh.get('token')
            return gh_token
    except Exception:
        return None
    return None


def _update_github_token(token):
    """Update the GitHub token in .secrets.toml file"""
    import toml
    import os
    
    repo_root = find_repo_root(Path.cwd())
    sec_path = repo_root / 'pr_agent' / 'settings' / '.secrets.toml'
    
    # Ensure the directory exists
    sec_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing data or create new
    data = {}
    if sec_path.is_file():
        try:
            data = toml.load(sec_path)
        except Exception:
            data = {}
    
    # Update the github token
    if 'github' not in data:
        data['github'] = {}
    data['github']['user_token'] = token
    
    # Write back to file
    try:
        with open(sec_path, 'w') as f:
            toml.dump(data, f)
        return True
    except Exception as e:
        raise Exception(f"Failed to write token: {str(e)}")


def _ensure_vuln_workflow(owner: str, repo: str, token: str):
    """Create or update the vulnerability scan workflow on the target repo via git commit."""
    workflow_filename = 'pr-agent-vuln-scan.yml'
    workflow_path = f'.github/workflows/{workflow_filename}'
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'token {token}'
    }

    # Plain string (no f-string) to avoid local interpolation of braces
    workflow_content = textwrap.dedent("""
name: PR-Agent Vulnerability Scan

on:
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install pip-audit
        run: |
          python -m pip install --upgrade pip
          pip install pip-audit

      - name: Run pip-audit
        run: |
          if [ -f requirements.txt ]; then
            pip-audit -r requirements.txt --format json --output vulnerability_report.json || true
          else
            pip-audit --format json --output vulnerability_report.json || true
          fi

      - name: Build markdown report
        run: |
          python - <<'PY'
          import json
          from datetime import datetime
          data = []
          try:
              with open('vulnerability_report.json') as f:
                  raw = json.load(f)
                  if isinstance(raw, dict) and 'dependencies' in raw:
                      data = raw.get('dependencies', [])
                  elif isinstance(raw, list):
                      data = raw
          except Exception:
              pass

          lines = ["# Vulnerability Scan Report", "", f"Generated: {datetime.utcnow().isoformat()} UTC", ""]
          total = sum(len((d.get('vulns', []) or [])) for d in data if isinstance(d, dict))
          lines.append(f"Total findings: **{total}**")
          lines.append("")
          lines.append("| Package | Version | Advisory | Fix Versions |")
          lines.append("| --- | --- | --- | --- |")

          for dep in data:
              if not isinstance(dep, dict):
                  continue
              name = dep.get('name', '?')
              ver = dep.get('version', '?')
              for vuln in dep.get('vulns', []) or []:
                  if not isinstance(vuln, dict):
                      continue
                  aliases = vuln.get('aliases') or []
                  advisory = vuln.get('id') or (aliases[0] if aliases else 'Unknown')
                  fix_versions = ', '.join(vuln.get('fix_versions') or ['None'])
                  lines.append(f"| {name} | {ver} | {advisory} | {fix_versions} |")

          with open('vulnerability_report.md', 'w') as f:
              f.write('\n'.join(lines))
          PY

      - name: Create PR with report
        uses: peter-evans/create-pull-request@v6
        with:
          branch: pr-agent/vuln-scan
          commit-message: "Add vulnerability scan report"
          title: "Add vulnerability scan report"
          body: "Automated vulnerability scan report generated by PR-Agent UI."
          add-paths: |
            vulnerability_report.json
            vulnerability_report.md
""").lstrip()

    # Clone the target repo to a temp directory and commit the workflow
    import tempfile
    import subprocess
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Clone the target repo
            clone_url = f'https://x-access-token:{token}@github.com/{owner}/{repo}.git'
            subprocess.run(['git', 'clone', clone_url, tmpdir], 
                          capture_output=True, text=True, timeout=30, check=True)
            
            # Create .github/workflows directory
            wf_dir = Path(tmpdir) / '.github' / 'workflows'
            wf_dir.mkdir(parents=True, exist_ok=True)
            
            # Write the workflow file
            wf_file = wf_dir / workflow_filename
            wf_file.write_text(workflow_content, encoding='utf-8')
            
            # Configure git and commit
            subprocess.run(['git', 'config', 'user.email', 'pr-agent@example.com'], 
                          cwd=tmpdir, capture_output=True, check=True)
            subprocess.run(['git', 'config', 'user.name', 'PR-Agent UI'], 
                          cwd=tmpdir, capture_output=True, check=True)
            subprocess.run(['git', 'add', str(wf_file)], 
                          cwd=tmpdir, capture_output=True, check=True)
            
            # Check if there are changes to commit
            status = subprocess.run(['git', 'status', '--porcelain'], 
                                   cwd=tmpdir, capture_output=True, text=True, check=True)
            if status.stdout.strip():
                subprocess.run(['git', 'commit', '-m', 'Add PR-Agent vulnerability scan workflow'], 
                              cwd=tmpdir, capture_output=True, check=True)
                subprocess.run(['git', 'push'], 
                              cwd=tmpdir, capture_output=True, check=True, timeout=30)
                print(f'[DEBUG] Workflow file committed and pushed: {workflow_filename}')
            else:
                print(f'[DEBUG] Workflow file already up to date: {workflow_filename}')
            
            return {'success': True, 'workflow_filename': workflow_filename}
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout or str(e)
            return {'success': False, 'error': f'Git operation failed: {error_msg}'}
        except Exception as e:
            return {'success': False, 'error': f'Failed to create workflow: {str(e)}'}


def _dispatch_vuln_workflow(owner: str, repo: str, token: str, workflow_filename: str = 'pr-agent-vuln-scan.yml'):
        """Trigger the vulnerability scan workflow via workflow_dispatch."""
        import requests
        import time
        headers = {
                'Accept': 'application/vnd.github+json',
                'Authorization': f'token {token}'
        }
        # get default branch
        repo_meta = requests.get(f'https://api.github.com/repos/{owner}/{repo}', headers=headers, timeout=10)
        if repo_meta.status_code != 200:
                return {'success': False, 'error': f'Failed to read repo metadata: {repo_meta.status_code} {repo_meta.text}'}
        default_branch = repo_meta.json().get('default_branch') or 'main'

        # Wait a bit for GitHub to index the workflow file
        time.sleep(2)
        
        print(f'[DEBUG] Attempting to dispatch workflow: {workflow_filename} on branch {default_branch}')
        dispatch_url = f'https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_filename}/dispatches'
        print(f'[DEBUG] Dispatch URL: {dispatch_url}')
        dispatch_resp = requests.post(dispatch_url, headers=headers, json={'ref': default_branch}, timeout=10)
        if dispatch_resp.status_code not in (200, 204):
                print(f'[DEBUG] Dispatch failed with status {dispatch_resp.status_code}')
                print(f'[DEBUG] Response: {dispatch_resp.text}')
                return {'success': False, 'error': f'Failed to dispatch workflow: {dispatch_resp.status_code} {dispatch_resp.text}'}

        html_url = repo_meta.json().get('html_url')
        runs_url = f"{html_url}/actions/workflows/{workflow_filename}"
        return {'success': True, 'workflow_url': runs_url, 'ref': default_branch}


def _build_markdown_report(audit_data, total_findings):
    lines = ["# Vulnerability Scan Report", "", f"Generated: {datetime.utcnow().isoformat()} UTC", ""]
    if total_findings == 0:
        lines.append("No vulnerabilities were detected by pip-audit.")
        return "\n".join(lines)

    lines.append(f"Total findings: **{total_findings}**")
    lines.append("")
    lines.append("| Package | Version | Advisory | Fix Versions |")
    lines.append("| --- | --- | --- | --- |")

    for dep in audit_data:
        if not isinstance(dep, dict):
            continue
        vulns = dep.get('vulns', []) or []
        for vuln in vulns:
            if not isinstance(vuln, dict):
                continue
            alias = None
            aliases = vuln.get('aliases') or []
            if aliases:
                alias = aliases[0]
            advisory = vuln.get('id') or alias or 'Unknown'
            fix_versions = ', '.join(vuln.get('fix_versions') or ['None'])
            lines.append(f"| {dep.get('name','?')} | {dep.get('version','?')} | {advisory} | {fix_versions} |")

    lines.append("")
    lines.append("This report was generated automatically by the PR-Agent UI vulnerability scan.")
    return "\n".join(lines)


def _run_local_vulnerability_scan(repo_root: Path):
    """Run pip-audit against the repo and build a report."""
    pip_audit_path = shutil.which('pip-audit')
    if not pip_audit_path:
        return {
            'success': False,
            'error': 'pip-audit is not installed in the environment. Install it with "pip install pip-audit" and retry.'
        }

    cmd = [pip_audit_path, '--format', 'json']
    if (repo_root / 'requirements.txt').is_file():
        cmd.extend(['-r', 'requirements.txt'])

    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    # pip-audit returns 1 when vulnerabilities are found, so accept 0 or 1
    if result.returncode not in (0, 1):
        return {
            'success': False,
            'error': result.stderr.strip() or result.stdout.strip() or 'pip-audit failed without output'
        }

    stdout_fallback = result.stdout.strip() if result.stdout else ''

    try:
        audit_data = json.loads(result.stdout or '[]')
    except json.JSONDecodeError as exc:
        return {
            'success': False,
            'error': f'Failed to parse pip-audit output: {exc}',
            'raw_output': stdout_fallback or result.stderr.strip()
        }

    # Normalize both legacy list output and newer object-with-dependencies output
    if isinstance(audit_data, dict) and 'dependencies' in audit_data:
        audit_items = audit_data.get('dependencies') or []
    elif isinstance(audit_data, list):
        audit_items = audit_data
    else:
        return {
            'success': False,
            'error': 'Unexpected pip-audit output (expected list or object with dependencies).',
            'raw_output': stdout_fallback or result.stderr.strip()
        }

    safe_items = [item for item in audit_items if isinstance(item, dict)]
    if not safe_items and audit_items:
        return {
            'success': False,
            'error': 'pip-audit returned non-dictionary entries; cannot build report.',
            'raw_output': stdout_fallback or result.stderr.strip()
        }

    total_findings = sum(len((item.get('vulns', []) or [])) for item in safe_items)
    report_md_path = repo_root / 'vulnerability_report.md'
    report_json_path = repo_root / 'vulnerability_report.json'

    report_md = _build_markdown_report(safe_items, total_findings)
    report_md_path.write_text(report_md, encoding='utf-8')
    report_json_path.write_text(json.dumps(audit_data, indent=2), encoding='utf-8')

    return {
        'success': True,
        'total_findings': total_findings,
        'report_md': str(report_md_path),
        'report_json': str(report_json_path),
        'audit_data': safe_items
    }


def _push_branch_and_create_pr(repo_root: Path, owner: str, repo_name: str, report_files: list, base_branch: str):
    """Create a branch with the report, push it, and open a PR on GitHub."""
    token = _get_github_token()
    if not token:
        return {'success': False, 'error': 'GitHub token not configured. Set GITHUB_TOKEN or GH_TOKEN, or save it in settings.', 'pr_created': False}

    repo = Repo(repo_root)
    if repo.is_dirty(untracked_files=True):
        return {'success': False, 'error': 'Working tree has uncommitted changes. Commit or stash before scanning.', 'pr_created': False}

    branch_name = f"vuln-scan/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    head_to_restore = repo.active_branch.name if not repo.head.is_detached else None

    # ensure origin exists
    if not repo.remotes:
        return {'success': False, 'error': 'No git remote configured; cannot push branch.', 'pr_created': False}
    origin = repo.remotes[0]

    remote_url = None
    try:
        remote_url = next(iter(origin.urls))
    except Exception:
        remote_url = None

    if not remote_url:
        return {'success': False, 'error': 'Unable to resolve remote URL for pushing.', 'pr_created': False}

    auth_remote = remote_url
    if remote_url.startswith('https://'):
        auth_remote = f"https://x-access-token:{token}@" + remote_url.split('https://', 1)[1]

    try:
        repo.git.checkout('-B', branch_name)
        repo.index.add(report_files)
        repo.index.commit('Add vulnerability scan report')

        repo.git.push(auth_remote, f"{branch_name}:{branch_name}", force=True)

        # create PR
        import requests
        api = f'https://api.github.com/repos/{owner}/{repo_name}/pulls'
        pr_title = 'Add vulnerability scan report'
        body = 'Automated vulnerability scan report generated by PR-Agent UI.'
        headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'token {token}'
        }
        payload = {'title': pr_title, 'head': branch_name, 'base': base_branch, 'body': body}
        pr_resp = requests.post(api, json=payload, headers=headers, timeout=10)
        pr_url = None
        if pr_resp.status_code in (200, 201):
            pr_url = pr_resp.json().get('html_url')
        else:
            return {
                'success': False,
                'error': f'Push succeeded but PR creation failed: {pr_resp.status_code} {pr_resp.text}',
                'pr_created': False
            }

        return {'success': True, 'pr_created': True, 'pr_url': pr_url, 'branch': branch_name}
    finally:
        # switch back to original branch to avoid leaving the user detached
        if head_to_restore:
            try:
                repo.git.checkout(head_to_restore)
            except Exception:
                pass


@app.route('/api/github/repos')
def github_repos():
    """List repositories accessible by the configured GitHub token.
    Falls back to public repos if no token is provided.
    """
    import requests
    token = _get_github_token()
    headers = {'Accept': 'application/vnd.github+json'}
    if token:
        headers['Authorization'] = f'token {token}'

    repos = []
    try:
        # user repos (includes org repos the user has access to)
        url = 'https://api.github.com/user/repos?per_page=100&type=all'
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return jsonify({'error': f'GitHub API status {r.status_code}: {r.text}', 'repos': []}), 200
        items = r.json()
        for it in items:
            repos.append({
                'full_name': it.get('full_name'),
                'name': it.get('name'),
                'owner': it.get('owner', {}).get('login'),
                'private': it.get('private'),
                'html_url': it.get('html_url')
            })
        return jsonify({'error': None, 'repos': repos})
    except Exception as e:
        return jsonify({'error': str(e), 'repos': []}), 200


@app.route('/api/github/repos/<owner>/<repo>/prs')
def github_repo_prs(owner, repo):
    import requests
    token = _get_github_token()
    headers = {'Accept': 'application/vnd.github+json'}
    if token:
        headers['Authorization'] = f'token {token}'
    api = f'https://api.github.com/repos/{owner}/{repo}/pulls?state=open&per_page=100'
    try:
        r = requests.get(api, headers=headers, timeout=10)
        if r.status_code != 200:
            return jsonify({'error': f'GitHub API status {r.status_code}: {r.text}', 'prs': []}), 200
        items = r.json()
        prs = []
        for it in items:
            prs.append({
                'number': it.get('number'),
                'title': it.get('title'),
                'user': it.get('user', {}).get('login'),
                'html_url': it.get('html_url'),
                'created_at': it.get('created_at')
            })
        return jsonify({'error': None, 'prs': prs}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'prs': []}), 200


@app.route('/api/github/repos/<owner>/<repo>/setup-automation', methods=['POST'])
def setup_repo_automation(owner, repo):
    """Setup GitHub Actions workflow for automated PR review, describe, and improve."""
    import requests
    import base64
    
    token = _get_github_token()
    if not token:
        return jsonify({
            'error': 'GitHub token not configured. Please set GITHUB_TOKEN or GH_TOKEN environment variable, or add it to pr_agent/settings/.secrets.toml',
            'success': False
        }), 200
    
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'token {token}'
    }
    
    # Read the pr_agent code and docker files from current repo
    cwd = find_repo_root(Path.cwd())
    
    # Dockerfile content
    dockerfile_content = """FROM python:3.12-slim

RUN apt-get update && apt-get install --no-install-recommends -y git curl && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir . && rm pyproject.toml requirements.txt

ENV PYTHONPATH=/app
COPY pr_agent pr_agent
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
"""

    # Entrypoint script
    entrypoint_content = """#!/bin/bash
python /app/pr_agent/servers/github_action_runner.py
"""

    # Action.yml for composite action
    action_yml_content = """name: 'PR-Agent'
description: 'Automated PR review, description, and improvement suggestions'
branding:
  icon: 'award'
  color: 'green'
runs:
  using: 'docker'
  image: 'Dockerfile'
"""

    # Workflow content that calls REST API endpoints
    workflow_content = """name: PR-Agent Automation

on:
  pull_request:
    types: [opened, reopened, synchronize]

permissions:
  issues: write
  pull-requests: write
  contents: read

jobs:
  pr_agent_job:
    runs-on: ubuntu-latest
    name: Run PR-Agent via REST API
    env:
      PR_AGENT_API_URL: ${{ secrets.PR_AGENT_API_URL || 'https://66d789067540.ngrok-free.app' }}
      PR_URL: ${{ github.event.pull_request.html_url }}
    
    steps:
      - name: Generate PR Description
        run: |
          PAYLOAD=$(printf '{"pr_url":"%s"}' "$PR_URL")
          curl -X POST "$PR_AGENT_API_URL/api/v1/describe" \\
            -H "Content-Type: application/json" \\
            -d "$PAYLOAD" \\
            --max-time 300 || echo "Description generation failed or timed out"
      
      - name: Review PR Code
        run: |
          PAYLOAD=$(printf '{"pr_url":"%s"}' "$PR_URL")
          curl -X POST "$PR_AGENT_API_URL/api/v1/review" \\
            -H "Content-Type: application/json" \\
            -d "$PAYLOAD" \\
            --max-time 300 || echo "Review generation failed or timed out"
      
      - name: Suggest Improvements
        run: |
          PAYLOAD=$(printf '{"pr_url":"%s"}' "$PR_URL")
          curl -X POST "$PR_AGENT_API_URL/api/v1/improve" \\
            -H "Content-Type: application/json" \\
            -d "$PAYLOAD" \\
            --max-time 300 || echo "Improvement suggestions failed or timed out"
"""
    
    try:
        files_to_create = [
            {
                'path': '.github/workflows/pr-agent-automation.yml',
                'content': base64.b64encode(workflow_content.encode()).decode(),
                'message': 'Add PR-Agent automation workflow'
            }
        ]
        
        results = []
        
        # Create/update each file
        for file_info in files_to_create:
            file_path = file_info['path']
            file_content = file_info['content']
            commit_msg = file_info['message']
            
            check_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{file_path}'
            check_response = requests.get(check_url, headers=headers, timeout=10)
            
            if check_response.status_code == 200:
                # File exists, update it
                existing_data = check_response.json()
                sha = existing_data.get('sha')
                
                update_data = {
                    'message': commit_msg,
                    'content': file_content,
                    'sha': sha
                }
                
                update_response = requests.put(check_url, headers=headers, json=update_data, timeout=10)
                
                if update_response.status_code in [200, 201]:
                    results.append(f'{file_path} updated')
                else:
                    error_body = update_response.json() if update_response.text else {}
                    error_msg = error_body.get('message', update_response.text)
                    return jsonify({
                        'error': f'Failed to update {file_path}: {error_msg}. Make sure your GitHub token has "workflow" & "repo" scopes.',
                        'success': False,
                        'status': update_response.status_code
                    }), 200
            
            elif check_response.status_code == 404:
                # File doesn't exist, create it
                create_data = {
                    'message': commit_msg,
                    'content': file_content
                }
                
                create_response = requests.put(check_url, headers=headers, json=create_data, timeout=10)
                
                if create_response.status_code in [200, 201]:
                    results.append(f'{file_path} created')
                else:
                    error_body = create_response.json() if create_response.text else {}
                    error_msg = error_body.get('message', create_response.text)
                    return jsonify({
                        'error': f'Failed to create {file_path}: {error_msg}. Make sure your GitHub token has "workflow" and "repo" scopes.',
                        'success': False,
                        'status': create_response.status_code
                    }), 200
            
            else:
                error_body = check_response.json() if check_response.text else {}
                error_msg = error_body.get('message', check_response.text)
                return jsonify({
                    'error': f'Failed to check {file_path}: {error_msg}',
                    'success': False,
                    'status': check_response.status_code
                }), 200
        
        return jsonify({
            'success': True,
            'message': '. '.join(results),
            'action': 'created/updated',
            'files_created': [f['path'] for f in files_to_create]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 200


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/repos')
def repos():
    cwd = Path.cwd()
    root = find_repo_root(cwd)
    repo = get_repo_info(root)
    return jsonify([repo])


@app.route('/api/repos/<name>')
def repo_details(name):
    cwd = Path.cwd()
    root = find_repo_root(cwd)
    repo = get_repo_info(root)
    if repo['name'] != name:
        return jsonify({'error': 'repo not found'}), 404
    return jsonify(repo)


@app.route('/api/repos/<name>/prs')
def repo_prs(name):
    cwd = Path.cwd()
    root = find_repo_root(cwd)
    repo = get_repo_info(root)
    if repo['name'] != name:
        return jsonify({'error': 'repo not found'}), 404
    prs = get_open_prs(root)
    return jsonify(prs)


@app.route('/api/github/repos/<owner>/<repo>/vulnerability-scan', methods=['POST'])
def vulnerability_scan(owner, repo):
    """Trigger remote GitHub Actions vulnerability scan and PR creation."""
    try:
        token = _get_github_token()
        if not token:
            return jsonify({'success': False, 'error': 'GitHub token not configured. Set GITHUB_TOKEN or GH_TOKEN, or save it in settings.'}), 400

        ensure_resp = _ensure_vuln_workflow(owner, repo, token)
        if not ensure_resp.get('success'):
            return jsonify(ensure_resp), 200

        workflow_filename = ensure_resp.get('workflow_filename', 'pr-agent-vuln-scan-v2.yml')
        dispatch_resp = _dispatch_vuln_workflow(owner, repo, token, workflow_filename=workflow_filename)
        if not dispatch_resp.get('success'):
            return jsonify(dispatch_resp), 200

        return jsonify({
            'success': True,
            'scan_dispatched': True,
            'message': 'Workflow dispatched. A PR will be created by the action.',
            'workflow_url': dispatch_resp.get('workflow_url'),
            'ref': dispatch_resp.get('ref'),
            'workflow_filename': workflow_filename
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def stream_subprocess(cmd_list, cwd=None):
    process = subprocess.Popen(cmd_list, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                yield line
        process.stdout.close()
        rc = process.wait()
        yield f"\nProcess exited with code {rc}\n"
    except GeneratorExit:
        try:
            process.kill()
        except Exception:
            pass


@app.route('/api/run', methods=['POST'])
def run_action():
    data = request.get_json() or {}
    action = data.get('action')
    pr_url = data.get('pr_url')
    repo = data.get('repo')
    if action not in ('review', 'describe', 'improve'):
        return jsonify({'error': 'invalid action'}), 400

    cwd = find_repo_root(Path.cwd())
    # command: run CLI in pr_agent folder; pass repo if provided via --repo
    cli_cwd = cwd / 'pr_agent'
    cmd = ['python3', 'cli.py']
    if pr_url:
        cmd.append(f'--pr_url={pr_url}')
    cmd.append(action)
    return Response(stream_subprocess(cmd, cwd=str(cli_cwd)), mimetype='text/plain')


@app.route('/api/settings/github-token', methods=['GET', 'POST'])
def github_token_settings():
    """Get or update GitHub token configuration"""
    import os
    if request.method == 'GET':
        token = _get_github_token()
        # Return masked token or status
        if token:
            masked = token[:4] + '*' * (len(token) - 8) + token[-4:] if len(token) > 8 else '***'
            return jsonify({
                'configured': True,
                'token': masked,
                'source': 'environment' if os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN') else 'file'
            })
        else:
            return jsonify({
                'configured': False,
                'token': None,
                'source': None
            })
    
    elif request.method == 'POST':
        data = request.get_json() or {}
        token = data.get('token', '').strip()
        
        if not token:
            return jsonify({'error': 'Token cannot be empty', 'success': False}), 400
        
        # Validate token format (GitHub tokens typically start with ghp_, github_pat_, etc.)
        if len(token) < 20:
            return jsonify({'error': 'Token appears to be invalid (too short)', 'success': False}), 400
        
        try:
            _update_github_token(token)
            return jsonify({
                'success': True,
                'message': 'GitHub token updated successfully',
                'source': 'file'
            })
        except Exception as e:
            return jsonify({
                'error': str(e),
                'success': False
            }), 500


@app.route('/api/settings/oauth-config', methods=['GET'])
def oauth_config():
    """Get OAuth configuration status"""
    return jsonify({
        'enabled': bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET),
        'client_id': GITHUB_CLIENT_ID if GITHUB_CLIENT_ID else None
    })


@app.route('/auth/github')
def github_oauth_login():
    """Initiate GitHub OAuth flow"""
    if not GITHUB_CLIENT_ID:
        return jsonify({'error': 'GitHub OAuth not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET environment variables.'}), 400
    
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # GitHub OAuth authorization URL
    redirect_uri = url_for('github_oauth_callback', _external=True)
    scope = 'repo,workflow,user:email'
    
    github_auth_url = (
        f'https://github.com/login/oauth/authorize'
        f'?client_id={GITHUB_CLIENT_ID}'
        f'&redirect_uri={redirect_uri}'
        f'&scope={scope}'
        f'&state={state}'
    )
    
    return redirect(github_auth_url)


@app.route('/auth/github/callback')
def github_oauth_callback():
    """Handle GitHub OAuth callback"""
    import requests
    
    # Verify state to prevent CSRF
    state = request.args.get('state')
    if not state or state != session.get('oauth_state'):
        return render_template('oauth_result.html', success=False, error='Invalid state parameter')
    
    code = request.args.get('code')
    if not code:
        error = request.args.get('error', 'Unknown error')
        return render_template('oauth_result.html', success=False, error=f'OAuth failed: {error}')
    
    # Exchange code for access token
    try:
        token_url = 'https://github.com/login/oauth/access_token'
        redirect_uri = url_for('github_oauth_callback', _external=True)
        
        response = requests.post(token_url, data={
            'client_id': GITHUB_CLIENT_ID,
            'client_secret': GITHUB_CLIENT_SECRET,
            'code': code,
            'redirect_uri': redirect_uri
        }, headers={'Accept': 'application/json'}, timeout=10)
        
        if response.status_code != 200:
            return render_template('oauth_result.html', success=False, error=f'Failed to exchange code: {response.text}')
        
        data = response.json()
        access_token = data.get('access_token')
        
        if not access_token:
            error_msg = data.get('error_description', 'No access token received')
            return render_template('oauth_result.html', success=False, error=error_msg)
        
        # Save the token
        _update_github_token(access_token)
        
        # Clean up session
        session.pop('oauth_state', None)
        
        return render_template('oauth_result.html', success=True, token=access_token[:10] + '...')
        
    except Exception as e:
        return render_template('oauth_result.html', success=False, error=str(e))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
