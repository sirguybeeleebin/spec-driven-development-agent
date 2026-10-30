# Skills

Five skills in the shop project. One is the base language layer, loaded by every role in every session. Four are domain skills, loaded by the role that touches the domain.

The system prompt carries the process; the skill carries the domain.

[← back to README](../README.md)

| Skill | Domain | Applies to | Loaded by (shop config) |
|---|---|---|---|
| `python-developer` | Python language | every Python module — source, test, or package marker | all four roles |
| `sqlite-implementing` | SQLite | source code that opens a connection, runs a statement, or manages a transaction | researcher, implementer, fixer |
| `sqlite-testing` | SQLite | tests that build or assert a database | researcher, tester, fixer |
| `fastapi-implementing` | FastAPI | router factories and the module-level app | researcher, implementer, fixer |
| `fastapi-testing` | FastAPI | tests that drive an endpoint through `TestClient` | researcher, tester, fixer |

`python-developer` is mandatory for every role in every session — it is the base layer that defines module layout, imports, naming, docstrings, typing, commenting, and tracing. Every other skill adds domain rules on top of it. No domain skill replaces `python-developer`; a domain skill that disagrees with it is more specific and wins on the specific point, but only on that point.

The `skills:` list under `agents.<role>` in `AGENT.yaml` is informational. The engine does not enforce it — a role loads a skill at runtime through the `load_skill` tool, and the tool resolves the title against directories under `skills/`. The list exists so a reader of the config sees at a glance which skills the role is expected to need.

## How a skill is shaped

One directory per skill under `skills/`. The directory name is the title. Inside, a required `SKILL.md` and an optional `scripts/` subdirectory:

```text
skills/
└── python-developer/
    ├── SKILL.md
    └── scripts/          # optional
```

`SKILL.md` is free-form markdown. It typically starts with YAML frontmatter:

```yaml
---
name: python-developer
description: "MANDATORY for every Python task..."
license: MIT
compatibility: python>=3.12
metadata:
  layer: reference
  domain: language
---
```

The engine does not require the frontmatter; it is part of the content. The first non-empty line of the file becomes `Skill.description`, used in the skill catalogue shown to each role.

`scripts/` is optional. Files under it are listed by relative path and exposed to the role as `Skill.scripts`. The engine does not run them — a skill's body tells the role when to invoke a script.

## How a skill is loaded

One loader, one tool.

- **`SkillLoader(workspace).load()`** walks `workspace.root / "skills"` once per run and returns one `Skill` per directory that contains a `SKILL.md`. A missing `skills/` directory, a directory without `SKILL.md`, or an empty `SKILL.md` is a startup error.
- **`LoadSkillTool(skills)`** exposes the `load_skill` tool to every role that lists it. The tool takes a title, finds the matching `Skill`, and returns its content and script list as the tool result. The role reads the content and applies it to the current session.

The catalogue — the list of skill titles with one-line descriptions — is injected into each role's system prompt at startup. A role selects from the catalogue and calls `load_skill` for each skill it decides to apply.

## The `python-developer` skill

The base layer for every Python module in the project. Module layout (the fixed order of `__future__`, stdlib, third-party, local, constants, classes, functions). Package files — every directory that holds a module has an `__init__.py`; the file is empty by default. Imports — absolute, never relative, no wildcards. Naming — `snake_case` for modules and functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants. Typing — annotations on every parameter and every return, builtin generics, `X | None` instead of `Optional[X]`. Docstrings — one-sentence summary, then `Args:`/`Returns:`/`Raises:` when they add value. Errors — specific exception classes, `raise ... from e` when the original must survive, no bare `except`. Immutability — prefer `tuple` and `frozenset` for fixed values. Constants — annotated when the literal is not obvious, never a mutable module-level default. Control flow — guard clauses over nested `if`. Strings — f-strings, `pathlib.Path`, `textwrap.dedent` for indented multi-line literals.

## The `sqlite-implementing` skill

How to access SQLite from source code. One connection per component, stored on `self`. `?` placeholders and a parameter tuple for every statement — never `%`, `.format()`, f-strings, or concatenation. Never `BEGIN`/`COMMIT`/`ROLLBACK` as SQL text — the driver manages the implicit transaction. Multi-row writes commit once and roll back on exception. When the contract carries the DDL as a Python constant, the implementation copies it character-for-character from the signature block. `NOT NULL` is two words with a space; `notnull` is a `PRAGMA table_info` flag, not SQL syntax. `PRAGMA table_info` and `PRAGMA foreign_key_list` are the only way to read schema metadata; never parse `sqlite_master.sql`. Let `sqlite3.IntegrityError` propagate from a write; no custom exception hierarchy.

## The `sqlite-testing` skill

How to prepare and assert a SQLite database inside a pytest test. Fresh `sqlite3.connect(":memory:")` per test. Run DDL in dependency order — foreign-key tables before the tables that reference them. Insert `Given` rows with raw `INSERT INTO ... VALUES (?, ...)`, never with a SUT method — a test for `get` must fail because `get` is broken, not because `insert` is broken. `conn.commit()` so the act step sees a fully written database. When the symbol under test is the schema creator itself, the connection starts empty — the act step creates the tables. `check_same_thread=False` under `TestClient`. Assert schema facts through `PRAGMA table_info` and `PRAGMA foreign_key_list`, never by counting keyword occurrences in `sqlite_master.sql`.

## The `fastapi-implementing` skill

How to write a router factory. Two targets: a factory `make_<name>_router(service)` and a module-level application with a `lifespan`. No module-level `APIRouter()`, no `Depends()` — a router is a closure over exactly one service argument. Pydantic v2 models with `ConfigDict(extra="forbid")`, `frozen=True` for response models, `Field(..., title=..., description=..., examples=[...])` on every field. Every HTTP status code is a `starlette.status.*` constant, never an integer. The exception mapping is fixed: `ValueError` → `400`, `KeyError` → `404`, `sqlite3.IntegrityError` → `409`. Nothing else is wrapped. The lifespan opens one shared connection, applies the schema, builds repositories, services, and routers in that order, yields, and closes the connection in a finalizer.

## The `fastapi-testing` skill

How to drive an endpoint through `TestClient`. Fresh app and client per test — no shared state between tests. `app.include_router(make_<name>_router(service))` inside the test, over the real service built on a real `:memory:` connection. `check_same_thread=False` on the connection so the worker thread can use it. The `# Act` section is one `client.<method>(...)` call. The `# Check` section asserts `response.status_code` and then `response.json()` — never the other way around, because a wrong status makes the body assertion meaningless. A storage error from the service maps to a 4xx status, not a raised exception in the test.

[← back to README](../README.md)