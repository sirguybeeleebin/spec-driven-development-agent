---
name: fastapi-router-implementing
description: Implements a FastAPI router factory make_<name>_router(service) from the contract in # Interfaces — Protocols for every collaborator, request and response models, closures over the service, exception-to-status mapping, and starlette status codes. Use when the target is a file under routers/ that defines a router factory, or when # Interfaces declares make_<name>_router.
license: MIT
compatibility: python>=3.10, fastapi>=0.110, pydantic>=2
metadata:
  layer: reference
  domain: http
---

# FastAPI router implementing

## When to use

1. `# Target` is a file under `routers/` and `# Interfaces` declares `make_<name>_router`.
2. The router must call service contracts declared in `# Interfaces` — **and every such contract is defined in `# Target` as a `Protocol`, not imported from the module where a concrete class of the same name lives**.
3. `# Interfaces` names the request body fields, the response body fields, the service exceptions the router maps, and every `Protocol` for every collaborator the router uses.

A module-level `app` or `lifespan` is **not** a router — that is a different target. If `# Target` defines `app` and `lifespan`, this is the wrong skill.

## Protocols are defined in `# Target`, never imported

Every collaborator the router uses is declared in `# Interfaces` as a `Protocol`. Every such `Protocol` is **defined in `# Target`** — a `class <Name>(Protocol):` block with exactly the methods the router calls, as `# Interfaces` shows them.

A concrete class of the same name may exist in a module under `# Context map` — a module that has `class <Name>` with a body. That is a **different symbol** with a different role. The router never imports it. The router defines its own narrow `Protocol` with only the methods it uses.

This applies to **every** `Protocol` in `# Interfaces`, not just one. If `# Interfaces` declares three `Protocol`s for three collaborators, `# Target` defines all three, in `# Interfaces` order.

The import block of `# Target` **contains no line that names a `Protocol`**. A line `from <module> import <ProtocolName>` is a defect — delete it and write the `class` block instead.

## 1. Imports — plan the file, then write the block

The import block is the **first code** in the file, before any class, enum, model, or function. It must be **complete before any definition is written**. A name used in the body without an import or a definition in this file fails at runtime with `NameError` — after the request has already been sent.

### 1.1 Plan the file in reasoning first

Before typing a single import line, list three sets in your reasoning:

**Defined in this file** — every symbol `# Interfaces` declares, in this order:

1. **Every `Protocol` — one per collaborator the router uses.** A `class <Name>(Protocol):` block with the methods `# Interfaces` shows. **Never an import line.** A concrete class of the same name in `# Context map` is a different symbol — stays out of `# Target`.
2. Every Pydantic model (`BaseModel` subclass).
3. Every enum (`StrEnum` subclass).
4. The factory function `make_<name>_router`.

**Imported from stdlib** — every stdlib name the body will use:
- `Protocol` — if the file defines a `Protocol`
- `StrEnum` — if the file defines an enum
- `Callable` — if a signature annotates a callable
- `sqlite3` — **if and only if** a handler catches `sqlite3.IntegrityError`

**Imported from third-party** — every third-party name the body will use:
- `APIRouter` — always (the factory creates one)
- `HTTPException` — always (every mapped exception raises one)
- `status` — if any handler uses `status.HTTP_*`
- `BaseModel`, `ConfigDict`, `Field` — if the file defines Pydantic models

Also list **every identifier used inside a handler**: `sqlite3.IntegrityError`, `status.HTTP_*`, `HTTPException`, every model name, the factory's parameters.

### 1.2 From the plan, list each import — one by one

| Identifier used in the body | Import or definition |
|---|---|
| **`<ProtocolName>` from `# Interfaces`** | **Defined in `# Target`** — `class <Name>(Protocol):` block. **Never an `import` line.** A concrete class of the same name in `# Context map` is a different symbol — never imported. |
| `Protocol` | `from typing import Protocol` — required whenever the file defines a `Protocol` |
| `APIRouter` | `from fastapi import APIRouter` |
| `HTTPException` | `from fastapi import HTTPException` |
| `status.HTTP_*` | `from starlette import status` |
| `BaseModel` | `from pydantic import BaseModel` |
| `ConfigDict` | `from pydantic import ConfigDict` |
| `Field` | `from pydantic import Field` |
| `StrEnum` | `from enum import StrEnum` |
| `Callable` | `from typing import Callable` |
| `sqlite3.IntegrityError` | `import sqlite3` — required whenever an `except sqlite3.IntegrityError` clause exists |
| Any other name from `# Context map` | Import from the module path `# Context map` shows |

Combine imports from the same module: `from fastapi import APIRouter, HTTPException`; `from pydantic import BaseModel, ConfigDict, Field`; `from typing import Callable, Protocol`.

### 1.3 Import order

stdlib → third-party → local. Blank line between groups. `import sqlite3`, `from typing import ...`, `from enum import ...` sit in the stdlib group.

```python
import sqlite3
from enum import StrEnum
from typing import Callable, Protocol

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from starlette import status
```

### 1.4 Verify after the write

After the `append`, read the file once more. Walk the body and list every identifier:

- **Every `Protocol` in `# Interfaces`** → the body contains a `class <Name>(Protocol):` block with the methods from `# Interfaces`. **The import block contains no line that names a `Protocol`.** A line `from <module> import <ProtocolName>` is a defect — delete it and write the `class` block instead.
- `sqlite3` or `sqlite3.IntegrityError` → `import sqlite3` is in the import block.
- `status.HTTP_*` → `from starlette import status` is in the import block.
- `HTTPException` → `from fastapi import HTTPException` is in the import block.
- `APIRouter` → `from fastapi import APIRouter` is in the import block.
- `BaseModel`, `ConfigDict`, `Field` → from `pydantic`.
- `StrEnum` → `from enum import StrEnum`.
- `Callable` → `from typing import Callable`.
- `Protocol` → `from typing import Protocol`.
- Every model name used in the body → defined in this file, per `# Interfaces`.

Any identifier used but neither imported nor defined is a defect. Fix it with a `patch` before the final message.

## 2. Read the contract, not the implementation

1. `# Interfaces` is the only source of truth for: the factory name, **every `Protocol` the router uses**, the request model fields, the response model fields, the exception types the router maps, and the status codes.
2. `# Context map` names modules that exist — but only for names **not declared in `# Interfaces`**. **A name declared in `# Interfaces` — including every `Protocol` — is defined in `# Target`, never imported from a module in `# Context map`, even when a same-name concrete class is listed there.**
3. `# Sequence`, when present, shows the exact service calls and branches. `# Activity`, when present, shows the decision order and `raise` branches. Use them when present.
4. Do **not** `read` the service or repository implementation to learn signatures. Every `Protocol` in `# Interfaces` carries them.

## 3. Define the Protocols before anything else

For every `Protocol` in `# Interfaces`, in `# Interfaces` order:

1. Write a `class <Name>(Protocol):` block.
2. The block declares **only the methods the router calls** — the method set is exactly what `# Interfaces` shows.
3. Method signatures — parameter names, parameter types, return type, `Raises:` classes — copied verbatim from `# Interfaces`.
4. Method bodies are `...` — the router does not implement the collaborator, only declares the narrow contract it uses.
5. The `Protocol` class has a docstring — copied from `# Interfaces` when `# Interfaces` carries one.

**A `Protocol` is not a concrete class.** A module in `# Context map` may define `class <Name>` with a body — the router imports nothing from it. The `Protocol` in `# Target` is the router's own narrow view, decoupled from any implementation.

## 4. Determine the factory signature

1. The factory name is exactly the name declared in `# Interfaces` — copy it verbatim.
2. Parameters, in the order declared: the service (typed as the `Protocol` from `# Interfaces`) and any injected callable the contract names. Do not add parameters the contract does not name.
3. Return type: `APIRouter`.
4. The factory does not accept a database connection, a session, or a client.

## 5. Request and response models

If `# Interfaces` declares Pydantic models for the router:

1. **Request model** — `model_config = ConfigDict(extra="forbid")`. No `frozen`.
2. **Response model** — `model_config = ConfigDict(frozen=True, extra="forbid")`.
3. Every field uses `Field(...)`. Do not invent metadata the contract does not name.
4. Types come from `# Interfaces`.

If `# Interfaces` does **not** declare a model for an endpoint, do not create one — use plain Python types.

## 6. Router body

1. `router = APIRouter(prefix=<prefix>, tags=<tags>)` — `prefix` and `tags` from `# Interfaces`. If not named, use `APIRouter()` with no arguments.
2. For each route declared in `# Interfaces`, in order:
   - Decorator: `@router.<method>(<path>, status_code=status.HTTP_..., response_model=<Model>)`. Method, path, status come from `# Interfaces`.
   - Handler is a **closure over the factory arguments** — the service, the injected callable if present. No global, no concrete service import, no connection.
   - Handler body: **one** service call, wrapped in `try` when the service raises exceptions the router maps.
3. Return `router`.

## 7. Exception mapping

The exception-to-status mapping comes from `# Interfaces`. Read the `Raises:` block of the router factory, or the exception list the contract carries. **Do not assume a mapping** — `ValueError` may map to `400`, `422`, or `409` depending on the contract.

1. Map **only** the exceptions `# Interfaces` names. Others propagate.
2. `detail=str(exc)`. Do not invent a different message.
3. If any `except sqlite3.IntegrityError` clause exists, `import sqlite3` is required at the top of the file — see §1.2.

## 8. Status codes

1. `from starlette import status` — the only form.
2. Use `status.HTTP_*` at every call site: decorator's `status_code=`, `HTTPException`'s `status_code=`.
3. No integer literals — `201`, `404`, `409` in `status_code=` is a defect.
4. No direct constant import — `from starlette.status import HTTP_201_CREATED` is a defect.
5. No `from fastapi import status`.

## 9. Layering

1. The router file **defines** every `Protocol` from `# Interfaces` — a `class <Name>(Protocol):` block per collaborator — and imports only `fastapi`, `starlette.status`, `pydantic` (when models are local), `typing.Protocol`, `typing.Callable`, `enum.StrEnum`, and `sqlite3` (when catching integrity errors).
2. The router never imports `repositories/`, never opens a connection, never calls a repository method, **never imports a concrete service class or any class that could substitute for a `Protocol`**.
3. The router does not register itself on an `app` — the factory returns an `APIRouter`, the composition root attaches it.

## Anti-patterns

1. **Importing a concrete service class instead of defining the `Protocol`.** `from <service_module> import <ConcreteService>` — a defect. `# Interfaces` declares `<ConcreteService>` as a `Protocol`; `# Target` defines that `Protocol` with a `class <ConcreteService>(Protocol):` block. A concrete class of the same name in a module under `# Context map` is a different symbol — the router never imports it.
2. **Missing `Protocol` in the import block when the file defines a `Protocol`.** Every `class <Name>(Protocol):` block requires `from typing import Protocol` — add it to the import block. Same defect as any missing import — fails with `NameError` on the first request.
3. **Missing `import sqlite3` when a handler catches `sqlite3.IntegrityError`** — the most common `NameError` in a router file. §1.2 and §1.4 catch it before the final message.
4. **Missing `from starlette import status` when a handler uses `status.HTTP_*`** — same defect, different name.
5. **Importing a `Protocol` from `# Context map`** — any `from <module> import <ProtocolName>` line. The `Protocol` in `# Interfaces` is a definition task, not an import task.
6. **Module-level `APIRouter()` or `app.include_router(...)`** — the factory creates the router; the composition root attaches it.
7. **`Depends()`** — the factory takes the service as an argument.
8. **Integer status codes** — `status_code=201`, `HTTPException(status_code=404, ...)` are defects.
9. **`from fastapi import status`** — use `from starlette import status`.
10. **`from starlette.status import HTTP_...`** — the module name `status` must appear at every call site.
11. **Importing a repository or a database driver** in the router file.
12. **Unused imports** — `import sqlite3` without an `except sqlite3.IntegrityError`, a Pydantic import when no model is defined locally, `Protocol` when the file defines no `Protocol`.
13. **Inventing request or response fields** not declared in `# Interfaces`.
14. **Catching an exception** the contract does not name.
15. **A handler that calls more than one service method.**