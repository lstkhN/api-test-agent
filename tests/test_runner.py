import httpx, respx
from api_test_agent.models import TestCase as ApiTestCase
from api_test_agent.runner import ApiRunner

@respx.mock
def test_runner_checks_status_and_json():
    respx.get("https://service.test/users").mock(return_value=httpx.Response(200, json={"ok": True}))
    result = ApiRunner().run(ApiTestCase(name="users", method="GET", url="https://service.test/users", checks=["json"]))
    assert result.passed is True
    assert result.response_preview == {"ok": True}

@respx.mock
def test_runner_reports_wrong_status():
    respx.get("https://service.test/users").mock(return_value=httpx.Response(404))
    result = ApiRunner().run(ApiTestCase(name="users", method="GET", url="https://service.test/users", expected_status=200))
    assert result.passed is False
    assert "expected HTTP" in result.error
