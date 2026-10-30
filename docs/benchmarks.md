# Benchmarks

Each subdirectory is a self-contained workspace.

[← back to README](../README.md)

| Benchmark | Stack | Tasks | Document |
|---|---|---|---|
| `shop` | FastAPI · Pydantic · SQLite | 8 | [benchmarks/shop.md](benchmarks/shop.md) |

## Layout

```text
benchmarks/
└── <name>/
    ├── AGENT.md
    ├── AGENT.yaml
    ├── __init__.py
    ├── skills/
    │   └── <title>/SKILL.md
    ├── tasks/
    │   └── <id>.md
    └── workflows/
        └── <name>.md
```

## Running

```bash
cd benchmarks/shop
python ../../main.py run --workflow workflows/end_to_end.md --verbose
```

Generated files land next to `AGENT.yaml`. Exit code `0` when every task ended `DONE`.

## Adding

New directory under `benchmarks/` with `AGENT.md`, `AGENT.yaml`, `skills/`, `tasks/`, `workflows/`. `main.py run` picks it up by path. Add a document under `docs/benchmarks/<name>.md` and one row above.