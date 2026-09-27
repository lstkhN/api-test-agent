import json
from api_test_agent.reliability import contract_diff, ingest_jsonl, mask

def test_mask_redacts_sensitive_fields():
    assert mask({'email':'a@b.test','name':'QA'}) == {'email':'<redacted>','name':'QA'}

def test_contract_diff_finds_removed_endpoint(tmp_path):
    old = tmp_path/'old.json'; new = tmp_path/'new.json'
    old.write_text(json.dumps({'paths': {'/users': {'get': {}}}})); new.write_text(json.dumps({'paths': {}}))
    result = contract_diff(str(old), str(new))
    assert result['breaking'][0]['endpoint'] == 'GET /users'

def test_ingest_skips_bad_lines(tmp_path):
    src=tmp_path/'traffic.jsonl'; out=tmp_path/'out.jsonl'
    src.write_text('{"token":"secret"}\nnot-json\n')
    assert ingest_jsonl(str(src), str(out)) == 1
    assert '<redacted>' in out.read_text()
