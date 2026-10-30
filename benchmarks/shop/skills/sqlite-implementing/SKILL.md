---
name: sqlite-implementing
description: Implements a repository, DAO, or data-access class over one sqlite3.Connection that reads and writes rows of a single SQLite table with parameterized SQL, using column names taken verbatim from the schema. Use when the target file is a repository that wraps sqlite3.Connection and queries one table.
version: 1.1.0
tags:
  - sqlite
  - repository
  - data-access
  - python
license: MIT
compatibility: Python 3.10+, sqlite3
---

# SQLite Implementing

This skill helps write a repository class for one SQLite table. Table and column names come from the DDL. Parameters go through `?`.

## When to Use

Use this skill when the target file is a repository, DAO, or data-access class that:
- wraps `sqlite3.Connection`;
- queries one table;
- receives `conn` in `__init__`.

Do NOT use this skill when the target file is a test — use `sqlite-testing` instead.

## How to Work

1. **Read the target file.** Run `read` on `# Target file`. Record what is already there.
2. **Find the schema.** Run `ls migrations/`, then `cat migrations/*.sql`. Record the table name and every column name. If no `.sql` file exists, use column names from `Returns:` and the table name from the target file stem.
3. **Write the code.** With one `append`, add `__init__` and every method from `# Interfaces`. If a method already exists in the file — skip it. If a method exists but does not match `# Interfaces` — run `read`, then `patch`.
4. **Verify.** Run `read` on `# Target file`. Confirm every method from `# Interfaces` is present, every `?` has a matching tuple element, no `SELECT *`, no `commit()`, no `rollback()`, no `close()`, no `try/except`.

## Imports

Exactly two import lines at the top of the file. Nothing else.

```python
from __future__ import annotations

import sqlite3
```

Add `from datetime import datetime, timezone`, `import uuid`, or `import json` only when a method body actually uses that name. Never add `from typing import TYPE_CHECKING`, never add `from sqlite3 import Connection`, never add `if TYPE_CHECKING:` — the annotation `sqlite3.Connection` works with `from __future__ import annotations` without any extra import.

## Rules

1. **Imports.** Per the `## Imports` section. Two lines only, plus one optional line per stdlib module the body uses. No `TYPE_CHECKING`, no `Connection` alias, no project imports.
2. **`__init__` signature.** `def __init__(self, conn: sqlite3.Connection) -> None:` — exact, copied from `# Interfaces`. Not `Connection`, not `sqlite3.dbapi2.Connection`, not `Any`. Two statements inside: `self._conn = conn` and `self._conn.row_factory = sqlite3.Row`. No I/O, no defaults, no `try/except`.
3. **Single-row read.** `stmt = "SELECT <cols> FROM <table> WHERE <pk> = ?"`, `row = self._conn.execute(stmt, (<key>,)).fetchone()`, `if row is None: return None`, `return dict(row)`. Every column listed explicitly, never `SELECT *`. One `?`, one tuple element with a trailing comma.
4. **Bulk read.** `stmt = "SELECT <cols> FROM <table>"`, `rows = self._conn.execute(stmt).fetchall()`, `return [dict(row) for row in rows]`. An empty table returns `[]`, not `None`.
5. **Insert.** `stmt = "INSERT INTO <table> (<cols>) VALUES (?, ?)"`, `self._conn.execute(stmt, (<param_1>, <param_2>))`. One `?` per column, tuple order matches column order.
6. **Update.** `stmt = "UPDATE <table> SET <col_1> = ? WHERE <pk> = ?"`, `self._conn.execute(stmt, (<param_1>, <pk>))`. SET columns first, WHERE key last.
7. **Delete.** `stmt = "DELETE FROM <table> WHERE <pk> = ?"`, `self._conn.execute(stmt, (<pk>,))`. A missing row is not an error.
8. **Parameters.** Always a tuple through `?`. Never f-string interpolation.
9. **No `commit()` — ever.** The word "persist" in `Steps:` means "call `self._conn.execute(...)`". It does not mean "call `commit()`". Do not call `self._conn.commit()`, `self._conn.rollback()`, or `self._conn.close()` inside any method. The caller owns the transaction and the connection lifespan. A single `execute` is the entire body of every write method. If the method body has `execute(...)` followed by `commit()` — delete the `commit()` line.
10. **Exceptions.** Do not catch `sqlite3.IntegrityError` or `sqlite3.OperationalError`. They must propagate unchanged. No `try/except` around `execute`.
11. **Names.** Column and table names come only from the DDL. No guessed names.
12. **No extra code.** Every top-level name in the file is either a `# Declares` name or an import from the `## Imports` section. No helpers, no constants, no type aliases, no `if __name__ == "__main__"`, no `print`.

## Output Format

Return only the file code. No comments beyond what the Python syntax requires.

## Errors

| Symptom | Cause |
|---|---|
| `sqlite3.OperationalError: no such column` | column name is not in the DDL |
| `sqlite3.OperationalError: no such table` | table name is not in the DDL, or migrations were not applied |
| `sqlite3.ProgrammingError: Incorrect number of bindings` | number of `?` does not match the tuple length |
| `ValueError: dictionary update sequence` | `row_factory = sqlite3.Row` missing in `__init__` |
| `TypeError: tuple indices must be integers` | caller reads `row["col"]` from a raw tuple — same missing `row_factory` |
| `ImportError: cannot import name 'Connection' from 'sqlite3'` with `TYPE_CHECKING` | use `sqlite3.Connection` in the annotation — no import alias needed |
| transaction left open after a method call | a `commit()` was removed but `execute` was never called — check the method body |