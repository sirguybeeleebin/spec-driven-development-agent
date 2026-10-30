---
name: sqlite-implementing
description: >
  Implements SQLite access in Python source code — connection
  ownership, parameter binding, transaction lifecycle, row-to-dict
  conversion, and IntegrityError propagation. Use whenever the
  target imports sqlite3, defines a repository over a SQL table,
  executes INSERT, SELECT, UPDATE, or DELETE, or reads the schema
  before writing code.
license: MIT
compatibility: python>=3.10, sqlite3
metadata:
  layer: reference
  domain: database
---

# SQLite implementing

## When to use

1. The target imports `sqlite3` or holds a `sqlite3.Connection`.
2. The target defines a repository, DAO, or any class over a SQL table.
3. The target executes `INSERT`, `SELECT`, `UPDATE`, or `DELETE`.
4. The target reads the schema — migrations, DDL, `PRAGMA` — before writing SQL. **First action on such a target is a `bash` listing of the migration directory — never a `read` of a guessed file.**

## 1. Load the schema before writing SQL

SQL is only correct against a known schema. The schema lives in
migration files, and their filenames are not listed in
`# Context map` — the repository map indexes `.py` files, not SQL.

**Do not read a path you have not seen.** `read` on a guessed path
returns a result indistinguishable from an empty file. Code written
against a guessed schema fails at the first `INSERT` or `SELECT`,
far from the guess — and the failure looks like a bug in the code,
not in the guess. That costs a fix attempt that should never have
been needed.

### Default path — first action

**Call the `bash` tool with `ls migrations/ && cat migrations/*.sql`.**

This single call does two things:

- `ls migrations/` gives the authoritative set of filenames. A
  filename that does not appear in this listing does not exist.
- `cat migrations/*.sql` gives the full DDL in one call. The shell
  glob covers every file the listing showed — do not open files one
  at a time.

Then, from that DDL, extract: columns, types, `NOT NULL`,
`PRIMARY KEY`, `UNIQUE`, `CHECK`, `FOREIGN KEY`, `DEFAULT`.

### Why `bash` and not `read`

`read` cannot discover filenames — it requires the path as an
argument. **Any migration filename passed to `read` is a guess.**
`bash` is the only tool that can list a directory. Therefore the
first action on migrations is always a `bash` call, never a `read`
call. `read` is for files whose path you already know from a
listing, from `# Context map`, or from a `bash` output this session.

### If the listing is empty

If `bash: ls migrations/` shows no `.sql` files, stop and return
`GAP: no migrations found`. Do not fall back to a guessed filename.

### If a column the task names is missing

Write only against what the DDL defines. Migrations are the only
source of truth for the schema — not the task prose, not a sibling
repository, not a docstring, not memory.

## 2. Statements and parameters

Every SQL statement uses `?` placeholders and a parameter tuple:

```python
cursor.execute(
    "SELECT product_id, name, stock FROM products WHERE product_id = ?",
    (product_id,),
)
```

Never `%`, `.format()`, f-strings, or concatenation. Concatenation
interpolates the raw value into SQL — a value containing a quote
breaks the statement, and a value the caller controls becomes an
injection vector. `?` binding sends the value out-of-band, so the
driver handles quoting and type coercion.

## 3. Transactions

Never issue `BEGIN`, `COMMIT`, or `ROLLBACK` as SQL text. The
`sqlite3` driver opens an implicit transaction before the first DML
and manages the lifecycle itself. A `BEGIN` in the body raises
`sqlite3.OperationalError: cannot start a transaction within a
transaction` — every prior DML on the same connection has already
opened one.

1. **Atomicity is a pair of Python method calls:** `conn.commit()`
   on success, `conn.rollback()` on exception. Neither is SQL text.
2. **A method that owns atomicity** runs its statements, then one
   `conn.commit()`. On any exception, one `conn.rollback()` and
   re-raise unchanged.
3. **A method that does not own atomicity** calls neither
   `commit()` nor `rollback()`. Transaction control belongs to the
   caller that opened the connection.

Detailed rules and examples — `references/transactions.md`.

## 4. Rows and return values

Set the row factory once, in `__init__`:

```python
def __init__(self, conn: sqlite3.Connection) -> None:
    self.conn = conn
    self.conn.row_factory = sqlite3.Row
```

After that, `fetchone()` returns `sqlite3.Row | None` and
`fetchall()` returns `list[sqlite3.Row]`. Wrap at the call site:

```python
row = cursor.fetchone()
if row is None:
    return None
return dict(row)
```

`dict(row)` builds `{column: value}` because `sqlite3.Row` iterates
as `(column, value)` pairs. Do not call `dict(...)` on a raw tuple
— it raises `ValueError: dictionary update sequence element #N has
length K; 2 is required` the moment a string value is not exactly
two characters. Do not rebuild the mapping from
`cursor.description`.

Return-shape contract for CRUD methods:

1. Single-row lookup → `dict | None`.
2. Bulk lookup → `list[dict]`; empty list when there are no rows.
3. Insert / update → `None`. Let `sqlite3.IntegrityError` propagate.
4. Update with no matching row → raise `KeyError(id)` when
   `cursor.rowcount == 0`.

## 5. Schema DDL

The DDL lives in migration files, not in Python code. A `CREATE
TABLE` inlined in a Python module is a second source of truth that
drifts from the migrations — and the drift shows up at runtime, not
at review.

1. Never inline `CREATE TABLE` in a Python module.
2. Code that only reads or writes rows never runs `CREATE TABLE` —
   migrations have already run by the time a repository method
   executes.
3. Never rebuild DDL from `PRAGMA table_info`. The `notnull` column
   it returns is a `0`/`1` flag, not the SQL keyword; rebuilding
   produces `near "notnull": syntax error`.

Schema introspection details — `references/pragma.md`.

## 6. Errors

Let `sqlite3.IntegrityError` propagate from a write. No custom
exception around it — the service layer above decides how to map
it (409, 400, retry, …). No custom exception hierarchy around
`sqlite3` at all.

## References

- `references/transactions.md` — commit/rollback examples,
  atomicity ownership, failure paths.
- `references/pragma.md` — `table_info`, `foreign_key_list`,
  `index_list`, and why never to parse `sqlite_master.sql`.

## Anti-patterns

1. `BEGIN` / `COMMIT` / `ROLLBACK` as SQL text.
2. `%`, `.format()`, f-strings, or concatenation in SQL.
3. `dict(...)` on a raw tuple.
4. Second `row_factory` assignment outside `__init__`.
5. `CREATE TABLE` inlined in a Python module.
6. Rebuilding DDL from `PRAGMA table_info`.
7. Wrapping `sqlite3.IntegrityError` in a custom exception.
8. **`read` on a migration path.** `read` cannot list a directory;
   the filename you pass is a guess. List and cat migrations with
   `bash` in one call. Writing SQL against a guessed schema fails
   at the first `INSERT`, far from the guess.