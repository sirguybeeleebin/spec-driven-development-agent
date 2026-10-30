# spec-driven-development-agent

## Описание

Мультиагентная система разработки по спецификациям. Задача описывается markdown-файлом со спецификацией; граф задач задаёт порядок выполнения. Каждую задачу выполняют четыре специализированных агента, использующих только нужные компоненты спецификации и навыки.

## Документация

- [Протокол задачи](docs/task-protocol.md) — формат `.md`-файла задачи
- [Конституция](docs/constitution.md) — `AGENT.md` и правила проекта
- [Конфигурация](docs/configuration.md) — `AGENT.yaml` и роли
- [Структура проекта](docs/project-structure.md) — дерево директорий и назначение модулей

## Потоки выполнения

- [Поток агента](docs/flows/agent.md)
- [Поток задачи](docs/flows/task.md)
- [Поток воркфлоу](docs/flows/workflow.md)
- [Граф задач](docs/task-graph.md)

## Роли

- [Researcher](docs/roles/researcher.md)
- [Implementer](docs/roles/implementer.md)
- [Tester](docs/roles/tester.md)
- [Fixer](docs/roles/fixer.md)

## Структура рабочего пространства

```
.
├── AGENT.md
├── AGENT.yaml
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md
│       ├── scripts/
│       ├── references/
│       └── assets/
├── tasks/
│   └── <task-id>.md
└── workflows/
    └── <workflow-id>.md
```
