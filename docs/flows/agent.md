[← Назад к README](../../README.md)

---

# Поток работы агента

```mermaid
flowchart TD
    Start([Старт]) --> Init["Инициализация:<br/>session = []<br/>metrics = []"]
    Init --> MarkRunning["FSM: mark_running"]
    MarkRunning --> Prepare["Подготовка промптов"]
    Prepare --> Session["Первое user-сообщение"]
    Session --> Check{"Итерации<br/>остались?"}

    Check -->|"да"| Ask["Запрос к модели<br/>с инструментами"]
    Ask --> Record["Ответ и метрики<br/>в сессию"]
    Record --> Wants{"Есть вызовы<br/>инструментов?"}
    Wants -->|"нет"| MarkSuccess(["FSM: mark_success<br/>SUCCESS"])

    Wants -->|"да"| NextTool{"Есть ещё<br/>вызов?"}
    NextTool -->|"да"| Execute["Выполнить<br/>инструмент"]
    Execute --> Hooks["Применить<br/>хуки"]
    Hooks --> AppendTool["Результат<br/>в сессию"]
    AppendTool --> NextTool
    NextTool -->|"нет"| Check

    Check -->|"нет"| AddFinal["Финальная инструкция<br/>в сессию"]
    AddFinal --> AskFinal["Запрос к модели<br/>без инструментов"]
    AskFinal --> RecordFinal["Ответ и метрики<br/>в сессию"]
    RecordFinal --> MarkSuccess

    Prepare -.->|"исключение"| MarkError(["FSM: mark_error<br/>ERROR"])
    Session -.->|"исключение"| MarkError
    Ask -.->|"исключение"| MarkError
    Execute -.->|"исключение"| MarkError
    Hooks -.->|"исключение"| MarkError
    AskFinal -.->|"исключение"| MarkError

    style Start fill:#e8f4ff
    style MarkSuccess fill:#d8ffd8
    style MarkError fill:#ffe8e8
```

## Ключевые моменты

- **FSM управляет статусом агента.** `AgentFSM` живёт в `runners/agent.py` как протокол (`mark_running`, `mark_success`, `mark_error`, `status`) и передаётся в `AgentRunner` через конструктор. Каждый вызов `run` — один цикл `IDLE → RUNNING → SUCCESS | ERROR`.

- **`mark_running` вызывается до `try`.** Если FSM уже в терминальном состоянии — это ошибка вызывающего, и она пробрасывается наружу, а не превращается в `AgentResult(ERROR)`.

- **`mark_success` — в двух точках:** после раннего выхода (модель не запросила инструменты) и после финального запроса (итерации исчерпаны). Обе ведут к `AgentResult(status=SUCCESS)`.

- **`mark_error` — в одном месте:** в `except Exception`. Все исключения (подготовка промптов, вызов модели, выполнение инструмента, хук, финальный запрос) ведут к `AgentResult(status=ERROR)`.

- **`status` в `AgentResult` берётся из FSM.** Это единый источник истины: если передан кастомный FSM (для наблюдаемости или для тестов), статус в результате совпадает с тем, что FSM зафиксировал после последнего перехода.

- **`session` и `metrics` создаются до `mark_running`.** Любое исключение оставляет накопленное состояние в `AgentResult`.

- **Системный промпт добавляется к каждому запросу заново.** В `session` лежат только `USER`, `ASSISTANT` и `TOOL` сообщения; `SYSTEM` конструируется из `format_system(skills)` на каждой итерации.

- **Несколько вызовов инструментов в одном ответе модели** выполняются последовательно, в порядке следования. Для каждого: выполнение → цепочка хуков (результат каждого становится входом следующего) → добавление результата в `session` с `tool_call_id`.

- **Метрики** — по одному набору на каждый запрос к модели, включая финальный.

- **После исчерпания итераций** в `session` добавляется `USER`-сообщение с `final_user`, модель вызывается с `tools=[]`, ответ попадает в `session` и `metrics`, возвращается `SUCCESS`-результат.

- **`max_iterations = 0`.** Цикл не выполняется ни разу, управление сразу уходит на финальный запрос без инструментов, FSM проходит `IDLE → RUNNING → SUCCESS` без промежуточных итераций.

- **Хуки применяются только после выполнения инструментов в основном цикле.** Финальный запрос модель получает с пустым списком инструментов, хуки на него не влияют.

---

[Назад к README](../../README.md)