"""Contract drift, traffic observations and risk scoring."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any
from .models import TestCase, TestResult
from .spec import load_document

SENSITIVE = re.compile(r"(authorization|password|passwd|token|secret|email|phone|ssn|api[-_]?key)", re.I)
def mask(value: Any) -> Any:
    if isinstance(value, dict): return {k: ("<redacted>" if SENSITIVE.search(k) else mask(v)) for k,v in value.items()}
    if isinstance(value, list): return [mask(v) for v in value]
    return value

def ingest_jsonl(path: str, output: str) -> int:
    count = 0
    with open(path, encoding="utf-8") as src, open(output, "a", encoding="utf-8") as dst:
        for line in src:
            try: item = mask(json.loads(line)); dst.write(json.dumps(item, ensure_ascii=False) + "\n"); count += 1
            except json.JSONDecodeError: continue
    return count

def _paths(spec: dict) -> set[str]: return {f"{m.upper()} {p}" for p, ops in spec.get("paths", {}).items() if isinstance(ops, dict) for m in ops if m.lower() in {"get","post","put","patch","delete"}}
def contract_diff(old_source: str, new_source: str) -> dict[str, Any]:
    old, new = load_document(old_source), load_document(new_source)
    removed = sorted(_paths(old) - _paths(new)); added = sorted(_paths(new) - _paths(old))
    breaking = [{"change": "endpoint_removed", "endpoint": x, "risk": "clients receive 404; existing integrations can fail"} for x in removed]
    for route, methods in old.get("paths", {}).items():
        for method, old_op in (methods or {}).items():
            new_op = new.get("paths", {}).get(route, {}).get(method)
            if not new_op: continue
            old_required = set(old_op.get("parameters", []) and [p.get("name") for p in old_op.get("parameters", []) if p.get("required")])
            new_required = set(new_op.get("parameters", []) and [p.get("name") for p in new_op.get("parameters", []) if p.get("required")])
            for name in sorted(new_required - old_required):
                breaking.append({"change": "required_parameter_added", "endpoint": f"{method.upper()} {route}", "field": name, "risk": "existing clients may receive 400 without this parameter"})
    return {"breaking": breaking, "added": added, "old_endpoints": len(_paths(old)), "new_endpoints": len(_paths(new)), "fingerprint": hashlib.sha256(json.dumps(new, sort_keys=True).encode()).hexdigest()}

def explain(result: TestResult) -> dict[str, str]:
    if result.passed: return {"risk": "none", "explanation": "Observed response matches the expected contract."}
    risk = "high" if result.status in (401,403) else "medium"
    return {"risk": risk, "explanation": result.error or "Contract mismatch detected; inspect the response and endpoint ownership."}

def analyze_results(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text())
    results = data.get("results", data if isinstance(data, list) else [])
    return {"total": len(results), "failed": sum(not x.get("passed", False) for x in results), "risks": [explain(TestResult.model_validate(x)) for x in results if not x.get("passed", False)]}
