[← Назад к README](../README.md)

---

# Конфигурация

`AGENT.yaml` в корне workspace — настройки harness: какие модели использовать, какие tools и skills доступны каждой роли, сколько итераций разрешено.

## Структура

- `max_fix_attempts` — сколько раз fixer может попытаться починить упавший тест перед тем, как задача считается проваленной;
- `agents.<role>.provider` — параметры инференса: `base_url`, `api_key`, `model`, `temperature`;
- `agents.<role>.tools` — список tool-имён, доступных роли;
- `agents.<role>.skills` — список skill-имён, которые роль загружает;
- `agents.<role>.max_iterations` — потолок итераций роли.

`<role>` — одно из `researcher`, `implementer`, `tester`, `fixer`.

Доступные tools: `bash`, `read`, `append`, `patch`, `load_skill`.

## Пример

```yaml
max_fix_attempts: 3

agents:
  researcher:
    provider:
      base_url: http://192.168.50.236:8080/v1
      api_key: none
      model: Qwen3-Coder-30B-A3B-Instruct-Q4_K_M
      temperature: 0.2
    tools:
      - bash
    skills: []
    max_iterations: 10

  implementer:
    provider:
      base_url: http://192.168.50.236:8080/v1
      api_key: none
      model: Qwen3-Coder-30B-A3B-Instruct-Q4_K_M
      temperature: 0.2
    tools:
      - read
      - append
      - patch
      - load_skill
      - bash
    skills:
      - sqlite-implementing
      - service-implementing
      - fastapi-router
    max_iterations: 30

  tester:
    provider:
      base_url: http://192.168.50.236:8080/v1
      api_key: none
      model: Qwen3-Coder-30B-A3B-Instruct-Q4_K_M
      temperature: 0.2
    tools:
      - append
      - load_skill
      - bash
      - read
    skills:
      - sqlite-testing
      - testing-with-mocks
      - fastapi-router-testing
    max_iterations: 15

  fixer:
    provider:
      base_url: http://192.168.50.236:8080/v1
      api_key: none
      model: Qwen3-Coder-30B-A3B-Instruct-Q4_K_M
      temperature: 0.2
    tools:
      - read
      - patch
    skills: []
    max_iterations: 10
```

## Валидация

Harness проверяет конфиг до запуска: неизвестный tool или skill, пустой provider, `max_iterations <= 0` — `ValueError` до первого обращения к модели.

---

[Назад к README](../README.md)