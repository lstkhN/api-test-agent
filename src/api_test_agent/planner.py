"""Deterministic plan generation: positive, negative and regression cases."""
from __future__ import annotations
from typing import Any
from .models import TestCase, TestPlan
from .spec import load_document
METHODS = {"get", "post", "put", "patch", "delete"}

def example(schema: dict[str, Any] | None, required: bool = False) -> Any:
    if not schema: return None
    if "example" in schema: return schema["example"]
    if "default" in schema: return schema["default"]
    if schema.get("enum"): return schema["enum"][0]
    typ = schema.get("type")
    if typ == "object": return {k: example(v, k in schema.get("required", [])) for k,v in schema.get("properties", {}).items() if required or k in schema.get("required", [])}
    if typ == "array": return [example(schema.get("items", {}))]
    return {"integer": 1, "number": 1.0, "boolean": True, "string": "qa-agent"}.get(typ)

def _status(op: dict) -> int:
    for code in op.get("responses", {"200": {}}):
        try: return int(code)
        except ValueError: continue
    return 200

def _response_schema(op: dict, status: int) -> dict | None:
    response = op.get("responses", {}).get(str(status), {})
    content = response.get("content", {}) if isinstance(response, dict) else {}
    item = content.get("application/json") or next(iter(content.values()), {})
    return item.get("schema") if isinstance(item, dict) else None

def generate_plan(source: str, base_url: str | None = None, auth_env: str | None = "API_AGENT_TOKEN") -> TestPlan:
    spec = load_document(source)
    base = (base_url or spec.get("servers", [{}])[0].get("url", "http://localhost:8000")).rstrip("/")
    cases: list[TestCase] = []
    for route, methods in spec.get("paths", {}).items():
        if not isinstance(methods, dict): continue
        for method, operation in methods.items():
            if method.lower() not in METHODS or not isinstance(operation, dict): continue
            url = base + "/" + route.lstrip("/")
            query: list[str] = []
            missing_required: str | None = None
            for p in operation.get("parameters", []):
                if not isinstance(p, dict): continue
                value = example(p.get("schema"), p.get("required", False)) or "1"
                if p.get("in") == "path": url = url.replace("{" + p.get("name", "") + "}", str(value))
                elif p.get("in") == "query" and p.get("required"):
                    query.append(f"{p.get('name')}={value}"); missing_required = p.get("name")
            if query: url += "?" + "&".join(query)
            security = operation.get("security", spec.get("security", []))
            content = operation.get("requestBody", {}).get("content", {})
            body = example(next(iter(content.values())).get("schema", {}), True) if content else None
            expected = _status(operation)
            checks = ["json"] if _response_schema(operation, expected) or "json" in str(operation.get("responses", {})).lower() else []
            name = operation.get("operationId", f"{method.upper()} {route}")
            cases.append(TestCase(name=name, method=method.upper(), url=url, body=body, expected_status=expected, checks=checks, expected_schema=_response_schema(operation, expected), auth_env=auth_env))
            # Authentication and IDOR probes are intentionally non-destructive.
            if security:
                cases.append(TestCase(name=f"{name} unauthenticated", method=method.upper(), url=url, body=body, expected_status=401, auth_env="__DISABLED__", negative=True))
            if "{" in route and method.lower() in {"get", "put", "patch", "delete"}:
                idor_url = url.replace("/1", "/99999999")
                cases.append(TestCase(name=f"{name} IDOR boundary", method=method.upper(), url=idor_url, body=body, expected_status=404, auth_env=auth_env, negative=True))
            # A missing required parameter is an explicit contract/security regression.
            if missing_required:
                cases.append(TestCase(name=f"{name} missing required {missing_required}", method=method.upper(), url=url.split("?")[0], body=body, expected_status=400, checks=[], auth_env=auth_env, negative=True))
    return TestPlan(target=base, cases=cases, warnings=[])
