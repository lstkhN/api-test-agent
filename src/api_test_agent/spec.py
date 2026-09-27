"""Input safety and small OpenAPI validation layer."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

MAX_BYTES = 2_000_000
MAX_PATHS = 500

def load_document(source: str) -> dict[str, Any]:
    path = Path(source)
    if path.exists():
        if path.stat().st_size > MAX_BYTES: raise ValueError("specification is larger than 2 MB")
        raw = path.read_text(encoding="utf-8")
    else: raw = source
    try: document = json.loads(raw)
    except json.JSONDecodeError as exc: raise ValueError("only valid JSON OpenAPI documents are supported") from exc
    validate_spec(document)
    return document

def validate_spec(document: Any) -> None:
    if not isinstance(document, dict) or not isinstance(document.get("paths"), dict):
        raise ValueError("specification must be an OpenAPI object with a paths object")
    if len(document["paths"]) > MAX_PATHS: raise ValueError("specification has too many paths")
    servers = document.get("servers", [])
    for server in servers:
        url = server.get("url", "") if isinstance(server, dict) else ""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
            raise ValueError("server URLs must be http(s) and must not contain credentials")
    for route in document["paths"]:
        if not isinstance(route, str) or not route.startswith("/") or len(route) > 1000:
            raise ValueError("invalid path in specification")
        if ".." in route.split("/"):
            raise ValueError("path traversal is not allowed")
