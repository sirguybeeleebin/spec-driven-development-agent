---
name: sqlite-testing
description: Tests the data layer. The target is a repository, DAO, or schema loader; the test opens a real sqlite3.connect, applies migrations, and asserts on real rows or schema facts. Use when the SUT's job is SQL and the test does not replace storage with mocks and does not import TestClient.
license: MIT
compatibility: python>=3.10, pytest>=8, sqlite3
metadata:
  layer: reference
  domain: database-testing
---

# SQLite testing with pytest

## When to use

1. The SUT is a repository, DAO, or schema loader — its job is SQL, not orchestration or HTTP.
2. The test opens `sqlite3.connect(":memory:")` and applies migrations.
3. The test asserts on real rows, real schema facts via `PRAGMA`, or a real `sqlite3.IntegrityError`.
4. The test does **not** use `MagicMock` for the storage layer and does **not** import `TestClient`.

A test that replaces storage with `MagicMock` opens no connection — it is not this layer. A test that imports `TestClient` goes through HTTP — it is not this layer. Only the data-layer test belongs here.

## 1. Test file shape

1. Every test is a module-level function `def test_<behavior>() -> None:`.
2. Never wrap tests in `class`, `unittest.TestCase`, or any container. The runner addresses tests as `<file>::<function>`; a method inside a class is `<file>::<Class>::<method>` and will not be found.
3. Do not import `unittest`. Do not use `self.assert*`. Use `assert` and `pytest.raises`.
4. All imports live inside the test function, at the top of its body. No module-level imports.
5. Import order inside the block: stdlib → `pytest` → module under test. One blank line after the block, before `# Given`.

Two templates below. Use the one that matches the scenario. **Every name used in the body must appear in its import block.**

Positive test — asserts on return value:

```python
def test_get_returns_product() -> None:
    import sqlite3
    from pathlib import Path
    from repositories.products import ProductRepository

    # Given
    ...
    # When
    ...
    # Then
    ...
```

Exception test — asserts that an exception is raised:

```python
def test_insert_duplicate_raises() -> None:
    import sqlite3
    from pathlib import Path
    import pytest
    from repositories.products import ProductRepository

    # Given
    ...
    # When & Then
    with pytest.raises(sqlite3.IntegrityError):
        ...
```

## 2. Imports — plan body, then import

**This is the most common failure mode.** A test body that uses a name not in the import block fails with `NameError` **after** the setup has already run. The tester has no `patch` tool and no `read` tool — a missing import cannot be fixed in place, only prevented in the plan.

### 2.1 Plan the body in your reasoning first

Before writing any code, write the skeleton as plain text:

```
# Given: <what setup runs>
# When: <the single SUT call>
# Then: <assertions, and whether any use pytest.raises>
```

Mark explicitly whether `Then` or `When & Then` uses `pytest.raises`. The plan is not code — it is a sentence per section.

### 2.2 From the plan, answer four questions

For every answer that is **yes**, add the import to the block:

| Question | Import |
|---|---|
| Does the body call `sqlite3.connect`, `sqlite3.IntegrityError`, or `conn.execute`? | `import sqlite3` |
| Does the body load migrations with `Path("migrations").glob(...)`? | `from pathlib import Path` |
| Does the body use `pytest.raises(...)`? | `import pytest` |
| Does the body reference the SUT class? | `from <module> import <Class>` |

If you answer "no" to all four, the body is empty — return to step 2.1.

### 2.3 Write the import block

Write the block **with every "yes" from 2.2**, before `# Given`, before setup SQL, before any assertion. Order: stdlib → `pytest` → module under test.

### 2.4 Verify before the write

Before the `append`, walk the planned body and list every identifier: classes, functions, modules, constants, types in annotations. Every identifier must appear in the import block or be a Python builtin (`dict`, `list`, `None`, ...). If an identifier is missing, return to §2.1 and revise the plan. Do not `append` until every identifier is accounted for.

The tester has no `patch` tool and no `read` tool. A test appended with a missing import **cannot be fixed in place** — it fails with `NameError`, the run moves on to the fixer, and the fixer burns a patch attempt on a test defect. Prevention in this step is the only way.

Do not import lazily in the middle of the body. Do not leave an import out because "I will add it later" — the test will not run.

## 3. Load migrations first

1. Run `ls migrations/ && cat migrations/*.sql` via the `bash` tool. `ls` cannot be fooled by a guessed filename; `read` on a nonexistent path may return empty and look like success.
2. For each `CREATE TABLE`, extract: columns, types, `NOT NULL`, `PRIMARY KEY`, `UNIQUE`, `CHECK`, `FOREIGN KEY`, `DEFAULT`.
3. Do not guess column names. Do not copy them from `# Scenario`, `# Interfaces`, docstrings, sibling repos, or memory.
4. Migrations are the only source of truth for DDL.
5. If a column in `# Scenario` is absent from every migration, do not invent it; assert only on what migrations define.
6. If no `CREATE TABLE` is visible after `bash: cat migrations/*.sql`, stop and return `GAP: migrations contain no DDL`. Do not guess.

## 4. Isolation

1. Fresh `sqlite3.connect(":memory:")` per test. Never module-level, never shared fixture.
2. Apply migrations inside the test. Never call `db.db.init` to prepare schema (except when the SUT is `init` itself).
3. Insert every `Given` row inside the test with raw SQL.
4. No test reads a row it did not insert.

## 5. Schema

Apply migrations in filename order inside the test:

```python
# requires: from pathlib import Path
for path in sorted(Path("migrations").glob("*.sql")):
    conn.executescript(path.read_text())
conn.execute("PRAGMA foreign_keys = ON")
conn.commit()
```

The `# requires:` line is not decoration — this block uses `Path`, so `from pathlib import Path` must be in the import block (§2). Copying the snippet without the import fails with `NameError: name 'Path' is not defined`.

1. Do not copy `CREATE TABLE` into the test.
2. Do not obtain DDL from application code.
3. Do not call a project initializer to prepare schema.
4. Do not rebuild DDL from `PRAGMA table_info`.

Exception — only when the task is implementing the schema initializer: start with an empty connection, call the initializer once as the act step, assert on `sqlite_master` and `PRAGMA` output.

## 6. Setup must satisfy the schema

For every setup `INSERT`, answer three questions from migrations only:

1. Which columns are required? — every `NOT NULL` without `DEFAULT`; every `CHECK` predicate.
2. Which values must be unique? — every `PRIMARY KEY` and `UNIQUE` column, across all setup rows in the test.
3. Which parent rows must exist? — every `FOREIGN KEY` column needs its target row present at insert time. Parent rows have the same three requirements; the chain cascades.

Insert rows in topological order: every parent row before every child row. Independent rows may go in any order.

## 7. Build the database

1. `conn = sqlite3.connect(":memory:")`. **Do not add `check_same_thread=False`.** The flag is required only when the connection crosses a thread boundary — that is, under `TestClient`. Repository tests run entirely in the main thread and do **not** need the flag. Adding it silently is a defect.
2. Apply migrations (§5), then `PRAGMA foreign_keys = ON`, then `conn.commit()`.
3. Insert every `Given` row with `conn.execute("INSERT INTO ... VALUES (?, ...)", (...))` in dependency order (§6).
4. `conn.commit()` after every setup step that opened a transaction.

## 8. Diagnose failures

A failing setup `INSERT` is a setup defect, not an SUT defect. Do not patch the SUT, do not weaken the assertion, do not disable the constraint.

| Error | Cause | Fix |
|---|---|---|
| `sqlite3.OperationalError: no such column` | Wrong column name | `bash: cat migrations/*.sql`; use exact names. |
| `sqlite3.IntegrityError: NOT NULL constraint failed: <t>.<c>` | Missing value | Add a value for `<t>.<c>`. |
| `sqlite3.IntegrityError: UNIQUE constraint failed: <t>.<c>` | Duplicate value | Make setup values distinct. |
| `sqlite3.IntegrityError: FOREIGN KEY constraint failed` | Parent row missing | Insert the parent row first (§6.3). |
| `sqlite3.IntegrityError: CHECK constraint failed: <name>` | Value violates a `CHECK` | Pick a value satisfying the `CHECK`. |
| `pytest: ERROR: not found: <file>::<name>` | Test is inside a class | Move to module level (§1.2). |
| `NameError: name '<X>' is not defined` | §2.1 plan omitted a name | §2.4 was skipped — the tester has no `patch` tool. In the next test, run §2.2 with the missing name in mind. |

## 9. Setup inserts are raw SQL

1. Rows go in with `conn.execute("INSERT INTO ...")`. Never call an SUT method in setup.
2. A non-SUT repository method is allowed in setup, followed by `conn.commit()`.
3. The act step calls exactly one SUT method — the one under test.
4. Do not skip parent rows because the scenario does not mention them.
5. Do not disable `PRAGMA foreign_keys` or `PRAGMA ignore_check_constraints`.
6. Do not add `DEFERRABLE` in the test; deferrability comes from migrations only.

## 10. Assert schema facts via PRAGMA

1. `PRAGMA table_info(<table>)` — columns, types, NOT NULL flags, PK positions.
2. `PRAGMA foreign_key_list(<table>)` — FKs.
3. `PRAGMA index_list(<table>)` — indexes.
4. Never read `sqlite_master.sql` and count keywords. Never assert on DDL string contents.

## 11. Exception tests

1. `import pytest` inside the function that calls `pytest.raises(...)`. The import is covered by §2.2 question 3 — answer "yes" as soon as the planned `Then` uses `pytest.raises`. Then §2.4 verifies it is present before the `append`.
2. Setup that satisfies the schema goes before the `with` block, never inside it.
3. Use the exact exception class named by `# Interfaces`; do not broaden to `Exception`, do not narrow to a subclass.
4. After the `with` block, assert the post-condition: row absent, row unchanged, or table empty.
5. Do not catch with `try/except` when `pytest.raises` is available.

## Anti-patterns

1. Module-level imports or module-level connection.
2. `class TestX` wrapper or `unittest.TestCase`.
3. Guessed column names not present in migrations.
4. Setup inserts inside `with pytest.raises`.
5. `PRAGMA foreign_keys = OFF` to bypass FK.
6. Lazy imports in the middle of the test body — write the full import block from §2.2 first.
7. `pytest.raises` used without `import pytest` — §2.2 question 3 was skipped.
8. `Path` used without `from pathlib import Path` — §2.2 question 2 was skipped.
9. `check_same_thread=False` added outside `TestClient` — the flag is only for connections that cross a thread boundary. Repository tests run in the main thread and must not set it.
10. `MagicMock` used for the storage layer in this test — a mocked storage means the test is not exercising the data layer.