"""Opt-in GitHub PR creation. Never runs git or sends secrets unless explicitly configured."""
from __future__ import annotations
import os
import httpx

def create_pull_request(repo: str, title: str, body: str, head: str, base: str = "main", dry_run: bool = True) -> dict:
    if dry_run: return {"dry_run": True, "repo": repo, "title": title, "head": head, "base": base}
    token = os.getenv("GITHUB_TOKEN")
    if not token: raise ValueError("GITHUB_TOKEN is required when --no-dry-run is used")
    response = httpx.post(f"https://api.github.com/repos/{repo}/pulls", headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}, json={"title": title, "body": body, "head": head, "base": base}, timeout=20)
    response.raise_for_status(); return response.json()
