from api_test_agent.planner import generate_plan

def test_generates_cases_and_examples():
    spec = '{"servers":[{"url":"http://test"}],"paths":{"/users/{id}":{"get":{"operationId":"get_user","parameters":[{"name":"id","in":"path","schema":{"type":"integer","example":42}}],"responses":{"200":{"content":{"application/json":{}}}}}}}}'
    plan = generate_plan(spec)
    assert len(plan.cases) >= 1
    assert plan.cases[0].url == "http://test/users/42"
    assert plan.cases[0].name == "get_user"
