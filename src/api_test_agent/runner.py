from __future__ import annotations
import os, time
from typing import Any
import httpx
from .models import TestCase, TestResult

def _shape(value: Any, schema: dict | None, path: str = "$") -> list[str]:
    if not schema: return []
    typ = schema.get("type")
    actual = "array" if isinstance(value, list) else "object" if isinstance(value, dict) else "boolean" if isinstance(value, bool) else "number" if isinstance(value, (int,float)) else "string" if isinstance(value, str) else "null"
    errors = [] if typ in (None, actual) or (typ == "number" and actual == "number") else [f"{path}: expected {typ}, got {actual}"]
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value: errors.append(f"{path}: missing required field {key}")
        for key, child in schema.get("properties", {}).items():
            if key in value: errors += _shape(value[key], child, f"{path}.{key}")
    return errors

class ApiRunner:
    def __init__(self, timeout: float = 10.0): self.timeout = timeout
    def run(self, case: TestCase) -> TestResult:
        started = time.perf_counter(); headers = dict(case.headers)
        if case.auth_env and os.getenv(case.auth_env): headers.setdefault("Authorization", "Bearer " + os.environ[case.auth_env])
        try:
            response = httpx.request(case.method, case.url, headers=headers, json=case.body, timeout=self.timeout)
            preview = None
            if response.content:
                try: preview = response.json()
                except ValueError: preview = response.text[:500]
            drift = _shape(preview, case.expected_schema)
            valid = response.status_code == case.expected_status and not drift
            error = None if valid else (f"expected HTTP {case.expected_status}, got {response.status_code}" if response.status_code != case.expected_status else "; ".join(drift))
            if valid and "json" in case.checks and "application/json" not in response.headers.get("content-type", ""): valid, error = False, "response is not JSON"
            return TestResult(test=case.name, method=case.method, url=case.url, status=response.status_code, duration_ms=round((time.perf_counter()-started)*1000,2), passed=valid, error=error, response_preview=preview, contract_drift=drift)
        except httpx.HTTPError as exc: return TestResult(test=case.name, method=case.method, url=case.url, duration_ms=round((time.perf_counter()-started)*1000,2), passed=False, error=str(exc))

def run_plan(cases: list[TestCase], timeout: float = 10.0) -> list[TestResult]: return [ApiRunner(timeout).run(case) for case in cases]
