---
name: sqlite-testing
description: Tests a repository, DAO, or data-access class against a real in-memory SQLite database, exercising CRUD, queries, and constraint handling through an actual sqlite3.Connection. Use when the target test exercises a class that wraps sqlite3.Connection.
version: 1.1.0
tags:
  - sqlite
  - testing
  - pytest
  - repository
  - python
license: MIT
compatibility: Python 3.10+, pytest 8+, sqlite3
---

# SQLite Testing

This skill helps write one pytest function per Gherkin scenario over a real `sqlite3.connect(":memory:")`. Table and column names come from the DDL. The test opens its own connection, applies the schema, inserts fixtures with raw SQL, calls the SUT once, and asserts on the result or on the database state.

## When to Use

Use this skill when the target test exercises a repository, DAO, or data-access class that:
- wraps `sqlite3.Connection`;
- queries one table;
- is constructed with `conn` in `__init__`.

## How to Work

1. **Read the target test file.** Run `read` on `# Target test file`. Record test functions already present. If `# Test function` is already there — go to Verify.
2. **Study the interface.** Read `# Interfaces`, `# Declares`, `# Gherkin`. Record the SUT class name, the constructor signature, the method under test, its `Returns:` shape, its `Raises:` classes. Classify the scenario: happy path (keywords *returns*, *creates*, *persists*, *reads*, *gets*, *lists*, *finds*) or raise path (keywords *raises*, *rejects*, *duplicate*, *constraint*, *invalid*, *missing*, *not found*).
3. **Find the migrations.** Run `ls` at the workspace root. Record every top-level directory. For every candidate directory in this order — `migrations/`, `db/migrations/`, `sql/`, `schema/`, `db/` — if it appears in the listing, run `ls <dir>/` and record every `.sql` file path. Stop at the first directory that contains `.sql` files directly. If no candidate directory contains `.sql` files, run `grep -rl "CREATE TABLE" --include="*.sql" .` and record every matched path. Record the directory that holds the migrations as `<migrations dir>` — the test will glob it.
4. **Read the migrations.** Run `cat <path>` for every `.sql` file recorded in step 3, one command per file. Record the table name, every column name, the primary key, every `NOT NULL` / `FOREIGN KEY` constraint, and every `DEFAULT`. These names are the only legal column names in any `SELECT` and any `INSERT` in the test. If step 3 found no `.sql` file, use column names from `Returns:` and the table name from `# Target file` stem, and record `<migrations dir>` as `_(none)_`.
5. **Write the test.** One `append` on `# Target test file` with one test function. Follow the `## Imports` section exactly — three imports on a happy path, five on a raise path.
6. **Verify.** Run `read` on `# Target test file`. Function name present exactly once. Every `Then` step from `# Gherkin` has a matching assertion. On a raise path, `import pytest` is present. On failure — one `patch`, then one `read`.

## Imports

Every import goes inside the test function, four-space indent, before the first executable statement. No module-level imports.

**Happy path** — the test calls the SUT and asserts on the result. Import exactly three lines:

```python
import sqlite3
from pathlib import Path
from <sut module> import <SutClass>
```

**Raise path** — the test wraps the SUT call in `pytest.raises(...)`. Import exactly five lines:

```python
import pytest
import sqlite3
from pathlib import Path
from <sut module> import <SutClass>
from <sut module> import <ExactClass>
```

`import pytest` and `from <sut module> import <ExactClass>` are only present on a raise path. On a happy path they are absent — `pytest` has nothing to do when no exception is expected.

`sut module` is the module path of the SUT class — for `repositories/orders.py` the module is `repositories.orders`. `<ExactClass>` is the exception class from `Raises:` recorded in step 2.

## Rules

1. **Imports.** Per the `## Imports` section. No module-level imports. `import pytest` on a raise path, absent on a happy path.
2. **Connection.** `conn = sqlite3.connect(":memory:")` first statement inside the function, then `conn.execute("PRAGMA foreign_keys = ON")` and `conn.row_factory = sqlite3.Row` immediately after. Without `PRAGMA foreign_keys = ON` every foreign-key constraint is silently ignored in `:memory:`. Without `row_factory = sqlite3.Row` every row is a tuple and `dict(row)` fails.
3. **Schema.** If `<migrations dir>` is not `_(none)_`, `for path in sorted(Path("<migrations dir>").glob("*.sql")): conn.executescript(path.read_text(encoding="utf-8"))` before any `INSERT`. Use the exact directory recorded in step 3 — never hardcode `migrations` when step 3 recorded a different path.
4. **Fixtures.** One `conn.execute("INSERT INTO <table> (<cols>) VALUES (?, ?, ...)", (<values>))` per row, columns from step 4, parameters through `?`, `conn.commit()` once after all inserts and before the SUT call.
5. **Happy path.** `sut = <SutClass>(conn=conn)`, then `result = sut.<method>(<args>)`, then assertions: `assert result is not None`, `assert len(result) == <N>`, `assert result["<key>"] == <expected>` per key from `Returns:`.
6. **Raise path.** All setup above the `with`, then `with pytest.raises(<ExactClass>): sut.<method>(<args>)`. Only the SUT call inside `with`.
7. **No `try/except`.** The test expects either a return or a raise, not both.
8. **No `conn.close()`.** The connection lives for the test body.
9. **No mocks for the connection.** `sqlite3.Connection` is a real resource — a mock returns a mock from `execute().fetchone()`, `dict(mock)` is `{}`, and assertions on the result fail with `assert 0 == N`. Use a real `:memory:` connection.

## Output Format

Return only the test function code. No comments beyond what the Python syntax requires.

## Errors

| Symptom | Cause |
|---|---|
| `sqlite3.OperationalError: no such table` | schema not applied — the `<migrations dir>` from step 3 returned no `.sql` files, or the glob path is wrong |
| `sqlite3.OperationalError: no such column` | column name is not in the DDL read in step 4 |
| `sqlite3.ProgrammingError: Incorrect number of bindings` | `?` count does not match the tuple length |
| `TypeError: tuple indices must be integers` | `row_factory = sqlite3.Row` missing |
| `NameError: name 'pytest' is not defined` | raise path without `import pytest` — the `## Imports` section for a raise path lists five imports, not three |
| `NameError: name '<ExactClass>' is not defined` | raise path without `from <sut module> import <ExactClass>` |
| `Failed: DID NOT RAISE <class '...'>` | setup inside the `with` block — move it above |
| `Failed: DID NOT RAISE sqlite3.IntegrityError` on a foreign-key scenario | `PRAGMA foreign_keys = ON` missing after `connect` — without it every FK constraint is silently ignored |
| `AssertionError: assert 0 == N` on `len(result)` | the connection is a mock — use a real `:memory:` connection |