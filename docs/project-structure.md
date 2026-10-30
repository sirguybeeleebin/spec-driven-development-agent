# Структура проекта

```
.
├── app/                            # конфигурация приложения: чтение конфига и сборка агентов
│   ├── config.py                   # чтение AGENT.yaml, AGENT.md и файлов задач
│   ├── config_test.py              # тесты чтения конфига
│   ├── factory.py                  # сборка AgentRunner из конфига, скиллов, провайдеров и hooks
│   ├── factory_test.py             # тесты сборки агентов
│   └── __init__.py                 # реэкспорт публичного API пакета
│
├── benchmark.sh                    # запуск инициализации и workflow для бенчмарка
│
├── docs/                           # документация проекта
│   ├── agent-flow.md               # поток работы агента
│   ├── configuration.md            # конфиг workspace
│   ├── constitution.md             # протокол составления конституции
│   ├── project-structure.md        # структура проекта
│   ├── roles/                      # описания ролей агентов
│   │   ├── fixer.md                # роль починки падающего теста
│   │   ├── implementer.md          # роль записи production-файла
│   │   ├── researcher.md           # роль исследования и плана
│   │   └── tester.md               # роль написания теста
│   ├── task-flow.md                # поток выполнения задачи
│   ├── task-graph.md               # граф задач и волны
│   ├── task-protocol.md            # формат файла задачи
│   └── workflow-flow.md            # поток выполнения workflow
│
├── hooks/                          # hooks, вызываемые после tool call
│   ├── __init__.py                 # реэкспорт PythonValidationHook
│   ├── python_validation.py        # валидация синтаксиса .py после append/patch
│   └── python_validation_test.py   # тесты валидации
│
├── llm/                            # клиент LLM
│   ├── client.py                   # обёртка над OpenAI-совместимым API с function calling
│   ├── client_test.py              # тесты клиента
│   └── __init__.py                 # реэкспорт публичного API пакета
│
├── main.py                         # CLI-точка входа
├── Makefile                        # команды разработки
│
├── models/                         # dataclass'ы, общие для всех слоёв
│   ├── agent.py                    # роли, статусы, результат агента
│   ├── graph.py                    # узлы, рёбра, граф
│   ├── __init__.py                 # реэкспорт всех моделей
│   ├── llm.py                      # сообщения, метрики, роли LLM, вызовы инструментов
│   ├── skill.py                    # структура скилла
│   ├── state.py                    # состояние, читаемое ролями
│   ├── task.py                     # задача, объявления, интерфейсы, sequence, gherkin
│   ├── test.py                     # результат запуска теста
│   ├── tool.py                     # перечисление инструментов
│   └── workflow.py                 # workflow и его результат
│
├── parsers/                        # парсеры markdown-файлов
│   ├── graph.py                    # парсер workflow
│   ├── graph_test.py               # тесты парсера workflow
│   ├── __init__.py                 # реэкспорт публичного API пакета
│   ├── skill.py                    # парсер скилла
│   ├── skill_test.py               # тесты парсера скилла
│   ├── task.py                     # парсер задачи
│   └── task_test.py                # тесты парсера задачи
│
├── promptproviders/                # сборка промптов по ролям
│   ├── fixer.py                    # провайдер промпта для роли починки
│   ├── fixer_test.py               # тесты провайдера починки
│   ├── implementer.py              # провайдер промпта для роли реализации
│   ├── implementer_test.py         # тесты провайдера реализации
│   ├── __init__.py                 # реэкспорт публичного API пакета
│   ├── researcher.py               # провайдер промпта для роли исследования
│   ├── researcher_test.py          # тесты провайдера исследования
│   ├── tester.py                   # провайдер промпта для роли тестирования
│   └── tester_test.py              # тесты провайдера тестирования
│
├── prompts/                        # шаблоны промптов для каждой роли
│   ├── fixer.py                    # system/user/final шаблоны для fixer
│   ├── implementer.py              # system/user/final шаблоны для implementer
│   ├── __init__.py                 # реэкспорт шаблонов
│   ├── researcher.py               # system/user/final шаблоны для researcher
│   └── tester.py                   # system/user/final шаблоны для tester
│
├── pyproject.toml                  # зависимости и настройки инструментов
├── README.md                       # общее описание проекта
│
├── runners/                        # циклы выполнения
│   ├── agent.py                    # цикл агента: модель ↔ инструменты
│   ├── agent_test.py               # тесты цикла агента
│   ├── __init__.py                 # реэкспорт публичного API пакета
│   ├── task.py                     # цикл задачи: роли и фикс-попытки
│   ├── task_test.py                # тесты цикла задачи
│   ├── workflow.py                 # цикл workflow: волны задач по графу
│   └── workflow_test.py            # тесты цикла workflow
│
├── testrunners/                    # запуск тестов как инструмента
│   ├── __init__.py                 # реэкспорт публичного API пакета
│   ├── pytest.py                   # имя тест-функции и запуск pytest
│   └── pytest_test.py              # тесты запуска
│
└── tools/                          # инструменты, доступные агентам
    ├── append.py                   # добавление содержимого в файл
    ├── append_test.py              # тесты добавления
    ├── bash.py                     # ограниченный shell с allowlist команд
    ├── bash_test.py                # тесты shell
    ├── __init__.py                 # реэкспорт публичного API пакета
    ├── load_skill.py               # загрузка содержимого скилла по имени
    ├── load_sjill_test.py          # тесты загрузки скилла (sic: имя файла)
    ├── patch.py                    # точечная замена подстроки в файле
    ├── patch_test.py               # тесты замены
    ├── read.py                     # чтение файла
    └── read_test.py                # тесты чтения
```

---

[Назад к README](../README.md)