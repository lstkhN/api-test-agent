"""Optional OpenAI-compatible planner. Rules remain the default for zero cost."""
from __future__ import annotations
import json
import os
import httpx
from .models import TestCase, TestPlan

class LLMPlanner:
    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.model = model or os.getenv("API_AGENT_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.getenv("API_AGENT_LLM_URL", "https://api.openai.com/v1")).rstrip("/")
        self.key = os.getenv("API_AGENT_API_KEY")

    def improve(self, spec: dict, plan: TestPlan) -> TestPlan:
        if not self.key: return plan
        prompt = "Create additional API negative/security test cases. Return JSON array of TestCase objects only.\n" + json.dumps({"spec": spec, "existing": [c.model_dump() for c in plan.cases]}, default=str)[:12000]
        response = httpx.post(self.base_url + "/chat/completions", headers={"Authorization": f"Bearer {self.key}"}, json={"model": self.model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}, timeout=30)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        content = content.replace("```json", "").replace("```", "").strip()
        extras = [TestCase.model_validate(item) for item in json.loads(content)]
        return plan.model_copy(update={"cases": plan.cases + extras, "generated_by": "llm"})
