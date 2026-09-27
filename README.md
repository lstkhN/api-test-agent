# API Reliability Agent

QA Automation / API / Python / LLM: система контроля надёжности API, а не только генератор тестов.

## Что проверяет

- OpenAPI-контракт и предыдущую версию (`diff`) с обнаружением удалённых endpoint'ов;
- реальные JSONL-логи запросов (`ingest`) с маскированием токенов, email, паролей и PII;
- текущие ответы API: статус, content-type и форму JSON (`contract drift`);
- positive, negative и regression-кейсы из обязательных параметров;
- auth через `API_AGENT_TOKEN` без попадания секрета в план или отчёт;
- результаты CI и объяснение риска (`analyze`);
- опциональное создание GitHub PR (только явный opt-in, по умолчанию dry-run);
- дешёвую OpenAI-compatible LLM для дополнительных security-кейсов.

## Быстрый старт

```bash
cd api-test-agent
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
api-agent plan examples/petstore.json
API_AGENT_TOKEN=secret api-agent run examples/petstore.json --report report.json
api-agent diff examples/petstore.json examples/petstore.json
api-agent analyze report.json
api-agent ingest production.jsonl --output traffic.jsonl
pytest -q
```

## GitHub PR

```bash
api-agent pr org/repo feature/api-regressions --title 'Add API regression tests'
# реальное создание только с явным флагом:
GITHUB_TOKEN=... api-agent pr org/repo feature/api-regressions --no-dry-run
```

`planner` — контракт → исполнимый план; `runner` — безопасное выполнение с timeout и auth; `reliability` — drift, traffic и risk; `llm` — опциональное расширение. Спецификации ограничены 2 MB, принимается только валидный JSON OpenAPI, server URL не может содержать credentials или опасную схему.
