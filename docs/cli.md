# CLI

One entry point: `main.py`. Commands: `info`, `init`, `config`, `run`.

[← back to README](../README.md)

| Command | Description | Example |
|---|---|---|
| `info` | Print the command table. | `python main.py info` |
| `init` | Create `skills/`, `tasks/`, `workflows/`; report `AGENT.md` / `AGENT.yaml` as present or missing. | `python main.py init` |
| `config set <key> <value>` | Set a top-level key in `AGENT.yaml`. Value is parsed as a YAML scalar. | `python main.py config set max_fix_attempts 5` |
| `config get <key>` | Print one top-level key. | `python main.py config get max_fix_attempts` |
| `config delete <key>` | Remove a top-level key. | `python main.py config delete max_fix_attempts` |
| `config clear` | Remove `AGENT.yaml`. | `python main.py config clear` |
| `run task <task_id>` | Run the pipeline for one task. The file is read from `tasks/<task_id>.md`. | `python main.py run task 001_products_repository` |
| `run workflow <workflow_id>` | Run the pipeline for every task in a workflow. The file is read from `workflows/<workflow_id>.md`. | `python main.py run workflow end_to_end` |

## Layout required for `run`

```text
project/
├── AGENT.yaml
├── AGENT.md
├── skills/
├── tasks/
└── workflows/
```

`run task` needs `AGENT.yaml` (with `repomap.max_tokens` and `agents`), the target task file under `tasks/`, and `skills/` (may be empty). `run workflow` needs the same plus the workflow file under `workflows/` and every task file the graph references.

## Exit codes

- `0` — the task ended `DONE`.
- `1` — the task ended `FAILED`, the workflow ended with at least one failed task, a required file was missing, or a parser or validator raised.

No fallbacks. A broken `AGENT.yaml`, a missing `skills/` directory, an empty `SKILL.md`, an unknown tool in `agents.<role>.tools`, or a skill listed under `agents.<role>.skills` but missing on disk each return `1` with the exact path or field on `stderr`. All error paths go through the same handler: `FileNotFoundError` and `ValueError` are printed as `error: <message>` and exit `1`.

## `AGENT.yaml`

```yaml
max_fix_attempts: 3

repomap:
  max_tokens: 2000

agents:
  researcher:
    provider:
      base_url: http://localhost:8080/v1
      api_key: none
      model: Qwen3-Coder-30B-A3B-Instruct-Q4_K_M
      temperature: 0.3
    tools: [read, load_skill]
    skills:
      - python-developer
    max_iterations: 10

  implementer:
    provider: { ... }
    tools: [read, append, patch, load_skill]
    skills:
      - python-developer
      - sqlite-implementing
      - fastapi-implementing
    max_iterations: 30

  tester:
    provider: { ... }
    tools: [append, load_skill]
    skills:
      - python-developer
      - sqlite-testing
      - fastapi-testing
    max_iterations: 15

  fixer:
    provider: { ... }
    tools: [read, patch, load_skill]
    skills:
      - python-developer
      - sqlite-implementing
      - sqlite-testing
      - fastapi-implementing
      - fastapi-testing
    max_iterations: 10
```

Three top-level keys:

- **`max_fix_attempts`** — optional non-negative integer. How many times `TaskRunner` re-runs the failing test after a fix. Default `3`.
- **`repomap`** — required mapping. One key: `max_tokens`, a positive integer that bounds the `# Context map` block.
- **`agents`** — required mapping with exactly four sub-keys: `researcher`, `implementer`, `tester`, `fixer`. Every missing role is a startup error.

Each role has three required keys and one optional key:

- **`provider`** — required mapping with four non-empty fields: `base_url`, `api_key`, `model`, `temperature`. Each role has its own endpoint; there is no shared default.
- **`tools`** — required non-empty list. Every name must be one of `read`, `append`, `patch`, `load_skill`. Unknown names are rejected at startup with `ValueError`.
- **`max_iterations`** — optional positive integer. Default `15`.
- **`skills`** — required list of skill titles. Every title must exist under `skills/<title>/SKILL.md`; a missing title is a startup error (`FileNotFoundError`). Each role's skills are the ones its `load_skill` tool will resolve; the tool is constructed at startup from this exact list and never scans the filesystem again.

## `AGENT.md`

Free-form markdown. No required sections, no schema, no reserved headings. `init` reports whether the file exists, but `run` does not currently read it — the `constitution` field on every parsed task defaults to an empty string.

## What `config` does not do

`config set`, `config delete`, and `config clear` edit `AGENT.yaml` at the top level. They do not validate the resulting configuration, and they do not accept dotted paths — only top-level keys like `max_fix_attempts` or `repomap`. A malformed value written through `config set` is caught at the next `run`, not at the moment of the edit. This is deliberate: `config` is a small editor, and validation belongs to the command that actually uses the config.

[← back to README](../README.md)