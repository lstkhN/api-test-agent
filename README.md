# API Reliability Agent

Инструмент для проверки надёжности HTTP API по OpenAPI-контракту. Он превращает JSON-описание API в воспроизводимый план проверок, выполняет запросы, проверяет ответы и помогает находить регрессии между версиями контракта.

Проект ориентирован на QA и CI: правила генерации тестов работают локально и не требуют LLM. LLM, обработка production-трафика и создание GitHub PR являются дополнительными возможностями.

## Возможности

- генерация positive-, negative- и regression-проверок из OpenAPI;
- проверка HTTP-статуса, `Content-Type` и базовой формы JSON-ответа;
- проверки неавторизованного доступа, обязательных параметров и границы IDOR для ресурсных URL;
- выполнение тестов с таймаутом и токеном из переменной окружения;
- сравнение двух версий контракта: удалённые endpoint'ы и новые обязательные параметры;
- импорт JSONL-трафика с маскированием чувствительных полей;
- анализ отчёта с краткой оценкой риска;
- необязательное добавление security-кейсов через OpenAI-compatible API;
- безопасный dry-run для GitHub PR (реальное создание включается явно).

## Требования и установка

- Python 3.10 или новее;
- доступ к тестируемому API для команды `run`;
- OpenAPI-документ в JSON (поддерживаются только валидные JSON-документы; YAML пока не поддерживается).

```bash
git clone <URL-репозитория>
cd api-test-agent
python3 -m venv .venv
. .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install -e '.[dev]'
```

После установки доступна команда `api-agent`.

## Быстрый старт

В репозитории есть пример `examples/petstore.json`:

```bash
# Сгенерировать план
api-agent plan examples/petstore.json --output test-plan.json

# Выполнить план и сохранить JSON-отчёт
api-agent run examples/petstore.json --report report.json

# Проанализировать неуспешные проверки
api-agent analyze report.json

# Проверить контракт без выполнения запросов
api-agent diff examples/petstore.json examples/petstore.json

# Запустить тесты проекта
pytest -q
```

По умолчанию URL берётся из первого элемента `servers` в OpenAPI. Его можно переопределить:

```bash
api-agent plan openapi.json --base-url http://localhost:8000 --output plan.json
api-agent run openapi.json --base-url http://localhost:8000 --timeout 5 --report report.json
```

## Команды

### `plan` — построить план

```bash
api-agent plan SPEC [--base-url URL] [--output FILE] [--llm]
```

`SPEC` — путь к JSON-файлу OpenAPI. По умолчанию результат записывается в `test-plan.json`. План содержит целевой URL, список кейсов, ожидаемый статус, тело запроса и схему ответа, если она указана в контракте. Генерация правилами детерминирована.

### `run` — выполнить проверки

```bash
api-agent run SPEC [--base-url URL] [--timeout SECONDS] [--report FILE] [--llm]
```

Команда сначала строит план, затем последовательно отправляет запросы. По умолчанию таймаут — 10 секунд, отчёт — `report.json`. В отчёте есть общее число кейсов, количество успешных и результаты каждого запроса.

Команда завершается кодом `1`, если хотя бы один кейс не пройден. Это позволяет использовать её в CI:

```bash
API_AGENT_TOKEN="$STAGING_API_TOKEN" \
  api-agent run openapi.json --base-url https://staging.example.com --report report.json
```

### `diff` — сравнить контракты

```bash
api-agent diff OLD.json NEW.json [--output FILE]
```

Выводит JSON с удалёнными и добавленными endpoint'ами, breaking changes, количеством endpoint'ов и fingerprint новой спецификации. Сейчас breaking change — это удаление endpoint'а или добавление нового обязательного параметра. При найденном breaking change команда завершается кодом `1`.

### `ingest` — обезличить JSONL-трафик

```bash
api-agent ingest traffic.jsonl --output traffic-redacted.jsonl
```

Каждая строка должна быть отдельным JSON-объектом. Корректные записи добавляются в выходной файл, некорректные JSON-строки пропускаются. Поля, чьи имена похожи на `authorization`, `password`, `token`, `secret`, `email`, `phone`, `ssn` или `api_key`, заменяются на `<redacted>`. Выходной файл открывается в режиме добавления, поэтому при повторном запуске записи дополняются.

### `analyze` — объяснить риск

```bash
api-agent analyze report.json
```

Команда считает количество ошибок и возвращает JSON со списком рисков. Неуспешные проверки со статусами `401`/`403` получают высокий риск, остальные — средний.

### `pr` — запросить GitHub PR

```bash
# Только показать параметры, ничего не создавая
api-agent pr OWNER/REPO feature/api-regressions \
  --title 'Add API regression tests'

# Реально создать PR — только с явным флагом
GITHUB_TOKEN="$GITHUB_TOKEN" api-agent pr OWNER/REPO feature/api-regressions \
  --base main --no-dry-run
```

Без `--no-dry-run` команда не обращается к GitHub API. Для реального создания необходим `GITHUB_TOKEN`. `head` — имя ветки с изменениями, `base` по умолчанию равен `main`.

## Авторизация и секреты

Если в операции контракта задана `security` (или глобальная `security`), план включает авторизованный кейс и неавторизованный кейс. Для авторизованного запроса значение `API_AGENT_TOKEN` передаётся как:

```http
Authorization: Bearer <значение API_AGENT_TOKEN>
```

Сам токен не записывается в план или отчёт. Не помещайте секреты в OpenAPI-файл, URL, логи или команды, сохранённые в истории shell.

## Дополнительные LLM-кейсы

Флаг `--llm` включает необязательное расширение плана. Для его работы задайте:

```bash
export API_AGENT_API_KEY='...'
export API_AGENT_MODEL='gpt-4o-mini'                         # необязательно
export API_AGENT_LLM_URL='https://api.openai.com/v1'         # необязательно
api-agent plan openapi.json --llm
```

Если `API_AGENT_API_KEY` не задан, используются только обычные правила. При включённом LLM спецификация и текущий план отправляются на указанный OpenAI-compatible endpoint; учитывайте это перед использованием закрытых контрактов.

## Формат и ограничения входных данных

- максимальный размер спецификации — 2 MB;
- максимум 500 путей;
- путь должен начинаться с `/`, не содержать `..` как сегмент и иметь длину не более 1000 символов;
- `servers[].url` должен использовать `http` или `https` и не содержать логин или пароль;
- поддерживаются HTTP-методы `GET`, `POST`, `PUT`, `PATCH`, `DELETE`;
- ссылки `$ref`, сложная валидация JSON Schema и YAML специально не разворачиваются — планировщик использует доступные локальные поля схемы.

## Как устроен проект

```text
src/api_test_agent/
├── cli.py          # команды api-agent
├── spec.py         # загрузка и базовая проверка OpenAPI JSON
├── planner.py      # детерминированная генерация TestPlan
├── runner.py       # HTTP-запросы и проверка TestResult
├── reliability.py  # diff, ingest и анализ рисков
├── llm.py          # необязательное LLM-расширение
└── github.py       # dry-run и создание GitHub PR
```

## Разработка

Установка зависимостей для разработки и запуск тестов:

```bash
python -m pip install -e '.[dev]'
pytest -q
```

Перед использованием в production проверьте сгенерированный план: negative-кейсы предполагают ожидаемые ответы `401`, `400` или `404`, а конкретное поведение API может отличаться.
