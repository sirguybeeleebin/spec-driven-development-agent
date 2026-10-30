# Stack

Python 3.12+, SQLite, FastAPI, Pydantic v2.

# Schema

Schema lives in `migrations/*.sql`. Read every `CREATE TABLE` before writing any query. Column names come from the DDL.

# Connection

One `sqlite3.Connection` per process, opened in the lifespan and closed in `finally`. Every repository receives the same connection. Tests use `with TestClient(app) as client:`.

# SQL

Every query uses `?` placeholders with a parameter tuple, bound to a variable named `stmt`.

# Errors

Every service declares its own exception hierarchy. Wrappers use `raise X(...) from exc`. Repositories let `sqlite3.IntegrityError` propagate unchanged.

# HTTP

Every status is `status.HTTP_*`. `make_<name>_router` returns the router; `app.include_router` lives in the composition root.

# Pydantic

Response models: `ConfigDict(extra="forbid", frozen=True)`. Request models: `ConfigDict(extra="forbid")`. Every field carries `Field(..., title=..., description=...)`. Every enum is `StrEnum`.

# Types

Every parameter and return value is annotated. `X | None`, never `Optional[X]`.

# Naming

`snake_case` for functions, methods, variables. `PascalCase` for classes. `UPPER_CASE` for constants. Test files: `<module>_test.py`. Test functions: `test_<scenario>`.

# Imports

Production modules: module-level. Test modules: inside `def test_<name>():`.

# Comments

Every logical block gets a comment stating why — the invariant, the failure prevented, the contract satisfied.