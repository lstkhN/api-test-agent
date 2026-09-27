from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class TestCase(BaseModel):
    name: str
    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = None
    expected_status: int = 200
    checks: list[str] = Field(default_factory=list)
    expected_schema: dict[str, Any] | None = None
    auth_env: str | None = None
    negative: bool = False

class TestResult(BaseModel):
    test: str
    method: str
    url: str
    status: int | None = None
    duration_ms: float
    passed: bool
    error: str | None = None
    response_preview: Any = None
    contract_drift: list[str] = Field(default_factory=list)

class TestPlan(BaseModel):
    target: str
    cases: list[TestCase]
    generated_by: Literal["rules", "llm"] = "rules"
    warnings: list[str] = Field(default_factory=list)
