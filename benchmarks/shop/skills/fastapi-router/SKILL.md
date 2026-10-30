---
name: fastapi-router
description: Creates a FastAPI APIRouter factory that closes over a service protocol, declares Pydantic request and response models in the router file, and maps typed service exceptions to HTTP status codes by class. Use when the target file defines a `make_<name>_router(service)` factory that registers endpoints under a router prefix.
version: 1.1.0
tags:
  - fastapi
  - router
  - pydantic
  - http
  - python
license: MIT
compatibility: Python 3.10+, FastAPI, Pydantic v2
---

# FastAPI Router

This skill helps write one router module: Pydantic request and response models declared in the file, the service protocol imported from its module, and a `make_<name>_router(service) -> APIRouter` factory that maps each typed exception to an HTTP status code by class.

## When to Use

Use this skill when the target file defines a router module that:
- exposes a `make_<name>_router(service)` factory;
- receives the service as a Protocol-typed parameter;
- registers one or more endpoints under a router prefix;
- maps service exceptions to HTTP status codes by class.

## How to Work

1. **Read the target file.** Run `read` on `# Target file`. Record top-level names already present. If the file is missing, every `# Declares` name is pending.
2. **Study the interface.** Read `# Interfaces`. For every name in `# Declares` record its type: `Protocol` (imported from the service module), `StrEnum`, response `BaseModel`, request `BaseModel`, or factory function. For every endpoint record: HTTP method, path, request model, response model, success status code. From `Raises:` blocks record every exception class and the HTTP status it maps to.
3. **Write the components.** One `append` per pending name, in this order: enum → response models → request models → factory. First `append` carries the import block. If a component already exists and matches `# Interfaces` — skip it.
4. **Verify.** Run `read` on `# Target file`. Every `# Declares` name is present exactly once. Every endpoint has `response_model=` and `status_code=status.HTTP_*`. Every `Raises:` class has its own `except` clause. The factory ends with `return router`.

## Imports

The import block at the top of the file has exactly these lines:

```python
from __future__ import annotations

from enum import StrEnum

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, ConfigDict, Field
```

After these four lines, add one line per module that declares the service protocol and the exception classes. For each such name, import it from the module recorded in `# Researcher result` — one line per module, grouping all names that come from the same module:

```
from <module that declares the name> import <Name1>, <Name2>, ...
```

The service protocol and every `Raises:` exception class come from these project imports. No Pydantic model is imported — every model is declared in this file. No concrete service, repository, or `sqlite3`.

## Rules

1. **Imports.** Per the `## Imports` section. Every project import comes from the module the researcher recorded for that name — never invented, never guessed.
2. **Enum.** `class <Name>(StrEnum):` with one line per member: `<MEMBER> = "<MEMBER>"`. Every member is `UPPER_SNAKE`, the value equals the name.
3. **Response model.** `class <Name>(BaseModel):` with `model_config = ConfigDict(extra="forbid", frozen=True)` and one `Field(..., title="<title>", description="<description>")` per field. Nested model fields are typed by class — `list[<OtherModel>]`, never `list[dict]`.
4. **Request model.** `class <Name>(BaseModel):` with `model_config = ConfigDict(extra="forbid")` and one `Field(..., title=..., description=...)` per field. Only client-supplied fields — no `created_at`, no `id`, no `status`.
5. **Factory.** `def make_<name>_router(service: <Protocol>) -> APIRouter:` with `router = APIRouter(prefix="/<resource>", tags=["<resource>"])` at the top, endpoints inside, `return router` at the end. Never attach the router.
6. **Handler.** `@router.<method>("<path>", response_model=<ResponseModel>, status_code=status.HTTP_<CODE>)` above `def <verb>(payload: <RequestModel>) -> <ResponseModel>:`. Plain verb name — `create`, `list`, `get`, `update`, `delete`. Service call inside `try`. Every `Raises:` class gets its own `except <Class> as exc: raise HTTPException(status_code=status.HTTP_<CODE>, detail=str(exc)) from exc`. Success returns `<ResponseModel>(**result)`.
7. **Dispatch by class.** No branch on `str(exc)`. No bare `except Exception`. No `JSONResponse` — always `HTTPException`. The unexpected path is FastAPI's default 500 handler.
8. **No extra code.** Every top-level name in the file is either a `# Declares` name or an import from the `## Imports` section. No helpers, no constants, no type aliases, no `app = FastAPI(...)`, no `app.include_router(...)`.

## Output Format

Return only the file code. No comments beyond what the Python syntax requires.

## Errors

| Symptom | Cause |
|---|---|
| `ImportError: cannot import name '<Model>' from '<module>'` | a model was imported — declare `class <Model>(BaseModel):` in this file per Rule 3 |
| `NameError: name '<ExceptionClass>' is not defined` | exception missing from the project import line per the `## Imports` section |
| `NameError: name 'status' is not defined` | `from fastapi import status` missing |
| `NameError: name 'HTTPException' is not defined` | `from fastapi.exceptions import HTTPException` missing |
| endpoint returns 500 where 400 expected | the validation `except` clause is absent or catches the wrong class — Rule 6 |
| endpoint returns 400 where 409 expected | dispatch branches on `str(exc)` instead of class — Rule 7 |
| `AssertionError: extra fields not permitted` on the response | `**result` contains a field not in the response model — align `Returns:` with the model |
| `TypeError: <Handler>() missing 1 required positional argument` | the handler was declared without `payload: <RequestModel>` per Rule 6 |