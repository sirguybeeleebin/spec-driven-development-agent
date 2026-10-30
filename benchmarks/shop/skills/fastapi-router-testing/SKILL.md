---
name: fastapi-router-testing
description: Tests a FastAPI router through TestClient — a real HTTP round-trip through the router, with the service replaced by a MagicMock — asserting status codes and response bodies for happy paths, validation failures, storage failures, and unexpected exceptions. Use when the target test exercises a router module that defines a `make_<name>_router(service)` factory and maps service exceptions to HTTP status codes by class.
version: 1.0.0
tags:
  - fastapi
  - testing
  - router
  - pytest
  - python
license: MIT
compatibility: Python 3.10+, FastAPI, pytest 8+, httpx
---

# FastAPI Router Testing

This skill helps write one pytest function per Gherkin scenario over a real `TestClient`. The router is mounted on a fresh `FastAPI()` app inside the test, the service is a `MagicMock`, and the test asserts on `response.status_code` and `response.json()`. Routing, request parsing, response serialization, and exception handlers run for real.

## When to Use

Use this skill when the target test exercises a router module that:
- defines a `make_<name>_router(service)` factory;
- receives the service as a Protocol-typed parameter;
- maps service exceptions to HTTP status codes by class;
- is mounted through `app.include_router(...)`.

## How to Work

1. **Read the target test file.** Run `read` on `# Target test file`. Record test functions already present. If `# Test function` is already there — go to Verify.
2. **Study the interface.** Read `# Interfaces`, `# Declares`, `# Gherkin`. Record the router factory name, the service protocol name, the endpoint (HTTP method + path), the request model and its required fields, the response model and its fields, and the mapping from each `Raises:` class to its HTTP status code. Classify the scenario: success (201), validation failure (400), storage failure (409), unexpected failure (500), or request-shape failure (422).
3. **Find the module paths.** The router module is the module of `# Target file` — for `routers/orders.py` the module is `routers.orders`. The service module is the module recorded in `# Researcher result` for the service protocol — the line marked `declared at <path>` for `<ServiceProtocol>`. Import the factory from the router module and the protocol and exception classes from the service module.
4. **Write the test.** One `append` on `# Target test file` with one test function. Follow the `## Imports` section exactly.
5. **Verify.** Run `read` on `# Target test file`. Function name present exactly once. Every `Then` step from `# Gherkin` has a matching assertion on `response.status_code` or `response.json()`. On a 500 scenario, `raise_server_exceptions=False` is present. On failure — one `patch`, then one `read`.

## Imports

Every import goes inside the test function, four-space indent, before the first executable statement. No module-level imports.

**Success (201) or failure (400, 409)** — the test reads `response.status_code` and `response.json()`. Import exactly six lines:

```python
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient
from <router module> import make_<name>_router
from <service module> import <ServiceProtocol>
```

For a 400 or 409 scenario, add `from <service module> import <ExactClass>` — one line per exception class the mock raises.

**Unexpected failure (500)** — the TestClient must not re-raise the server exception. Import the same six lines and open the client as `with TestClient(app, raise_server_exceptions=False) as client:`.

`import pytest` is never needed — a router catches every `Raises:` class and returns a `Response`. The test asserts on the response, not on an exception.

## Rules

1. **Imports.** Per the `## Imports` section. No module-level imports. No `pytest` — the router converts exceptions to responses.
2. **Mock the service.** `mock_service = MagicMock()` inside the test. For success: `mock_service.<method>.return_value = <dict with every key from Returns:>`. For 400 or 409: `mock_service.<method>.side_effect = <ExactClass>("<message>")`. For 500: `mock_service.<method>.side_effect = RuntimeError("<message>")`.
3. **Build a fresh app.** `app = FastAPI()`, then `app.include_router(make_<name>_router(mock_service))`. Inside the test, not at module scope.
4. **Open the client.** `with TestClient(app) as client:` for 201, 400, 409. `with TestClient(app, raise_server_exceptions=False) as client:` for 500 — without `raise_server_exceptions=False` the `RuntimeError` escapes `client.<method>` and the test fails before the assertion.
5. **One request per test.** `response = client.<method>("<prefix><path>", json={<request body>})`. The path includes the router prefix — for prefix `/orders` and route `/`, the full path is `/orders/`. The `json=` argument is a dict with every field the request model requires.
6. **Assert status first.** `assert response.status_code == status.HTTP_<CODE>_<NAME>`. Never an integer literal.
7. **Assert body keys.** `assert response.json()["<key>"] == <expected>` per key the scenario checks. For a failure scenario, `assert response.json()["detail"] == "<message>"`.
8. **No `pytest.raises`.** The router converts every `Raises:` class to `HTTPException` — the test reads the response, it does not catch an exception.
9. **No module-level app or client.** Each test creates its own `MagicMock`, `FastAPI()`, and `TestClient`.
10. **No `raise_server_exceptions` on 4xx.** For 400 and 409 the router catches the exception and returns a `Response` — the default `raise_server_exceptions=True` is correct because there is nothing to re-raise. Only 500 needs the flag set to `False`.

## Output Format

Return only the test function code. No comments beyond what the Python syntax requires.

## Errors

| Symptom | Cause |
|---|---|
| `RuntimeError: <message>` escapes `client.<method>` where 500 expected | `raise_server_exceptions=False` missing — open the client as `with TestClient(app, raise_server_exceptions=False) as client:` |
| `response.status_code == 500` where 400 or 409 expected | the mock raised a bare `Exception` instead of the typed subclass the router maps — use `<ExactClass>("<message>")` |
| `response.status_code == 422` where 201 expected | the request body is missing a required field — include every field the request model requires |
| `response.status_code == 404` | the path in `client.<method>` does not include the router prefix — `<prefix><path>`, not just `<path>` |
| `NameError: name 'pytest' is not defined` | `pytest` used unnecessarily — a router test does not use `pytest.raises` |
| `KeyError: 'detail'` on a 500 response | the router let the exception propagate — the default 500 handler has no `detail` key; assert only on `status_code` |
| `AttributeError: 'NoneType' object has no attribute '...'` inside the handler | `mock_service` was not passed to the router factory — `app.include_router(make_<name>_router(mock_service))` |
| `AssertionError: assert 'some message' in ''` | `response.json()` has no `detail` key — the router did not set `detail`, or the response body is empty |
| `TypeError: make_<name>_router() missing 1 required positional argument` | the factory was called without `mock_service` |