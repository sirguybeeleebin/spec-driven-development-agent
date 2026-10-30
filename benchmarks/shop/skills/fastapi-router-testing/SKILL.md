---
name: fastapi-router-testing
description: Tests a FastAPI router factory through TestClient with a MagicMock service. The test exercises the HTTP surface only — status codes, response body, request validation, and exception-to-status mapping — and never touches a real database, a real service, or a real lifespan. Use when the target is a router factory under routers/ and the test drives it through TestClient.
license: MIT
compatibility: python>=3.10, fastapi>=0.110, httpx>=0.27, pytest>=8, unittest.mock
metadata:
  layer: reference
  domain: http-router-testing
---

# FastAPI router testing

## When to use

1. The target is a router factory declared in `# Interfaces`.
2. The test builds a fresh `FastAPI()` app, mounts the router, and drives it through `TestClient`.
3. The service is a `MagicMock()` — no real service, no `sqlite3.connect`, no `lifespan`.
4. The test asserts `response.status_code`, `response.json()`, or that the service was called with the right arguments.

A test that opens `sqlite3.connect` is a data-layer test, not this one. A test that calls the service directly without `TestClient` is a business-logic test, not this one. Only the HTTP-surface test with a mocked service belongs here.

## 1. Imports — local, planned, complete

Imports live **inside** the test function. A module-level import is a defect.

### Plan the body in reasoning first

Write the skeleton as plain text:

```
# Given: service = MagicMock(); <each injected parameter> = <variable>; app; client; configure service
# When: one client.<method>(...)
# Then: assert status_code, json body, service calls
```

**Save every injected dependency in a variable before it goes into the factory.** If the factory takes the service and one more parameter, that parameter is a variable — `<dep> = <value>`. The same variable appears in `assert_called_once_with` in §5. An inline argument — `make_router(service, <inline value>)` — is a defect: the test has no reference to compare against and reaches for `ANY`.

Mark explicitly whether the body uses `pytest.raises` — usually not: HTTP errors are returned as `response.status_code`, not raised.

### From the plan, answer six questions

| Question | Import |
|---|---|
| Does the body use `TestClient`? | `from fastapi.testclient import TestClient` |
| Does the body use `FastAPI()`? | `from fastapi import FastAPI` |
| Does the body use `status.HTTP_*`? | `from fastapi import status` |
| Does the body construct `MagicMock(...)`? | `from unittest.mock import MagicMock` |
| Does the body use `ANY`? | `from unittest.mock import ANY` — same line as `MagicMock` when both are used: `from unittest.mock import ANY, MagicMock` |
| Does the body reference the router factory or a model declared in `# Interfaces`? | `from <module> import <Name>` — module path from `# Context map` |
| Does the body use `pytest.raises(...)`? | `import pytest` — only if the body actually calls it |

If all answers are "no", the body is empty — return to planning.

**`mock.ANY`, `mock.MagicMock`, `from unittest.mock import mock` are defects.** `mock` is the module name, not a name inside `unittest.mock`. There is no `mock.ANY` that resolves — the reference fails with `NameError: name 'mock' is not defined` if `mock` is not imported, and `ImportError` if it is imported from `unittest.mock`. Import the names directly: `from unittest.mock import ANY, MagicMock, call`.

### Import order inside the block

stdlib → `pytest` → `fastapi` / `TestClient` → `unittest.mock` → module under test. One blank line after the block, before `# Given`.

```python
def test_<behavior>() -> None:
    from fastapi import FastAPI, status
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock
    from <router_module> import <factory>

    # Given
    ...
```

### Verify after the write

After the `append`, read the file once more. Three checks:

1. Every `import` line sits inside a `def test_<...>()` body.
2. Every identifier in the body is covered by the import block or is a Python builtin.
3. **Every imported name is used in the body.** An unused import is a defect — it breaks `ruff` and `pylance`, and signals that the plan drifted.

A missing import fails with `NameError` after the setup has already run.

## 2. Setup — fresh app, fresh client, mocked service, saved injected dependencies

1. `service = MagicMock()` — one mock for the service the factory receives.
2. **For every injected parameter the factory takes besides the service, save the value in a variable first.** `<dep> = <value>` — the same variable is passed to the factory and used in §5 assertions.
3. `app = FastAPI()` — fresh per test, no `lifespan`, no module-level app.
4. `app.include_router(<factory>(service, <dep>, ...))` — mount the router, pass the saved variables by name.
5. `client = TestClient(app)` — one client per test.
6. Configure `service.<method>.return_value` or `service.<method>.side_effect` **before** the act step.

No module-level app, no shared client, no real connection, no real service, no inline value passed to the factory.

## 3. Configure the service mock

1. `service.<method>.return_value = <dict>` — the service returns a value the router will serialize into the response model. `<method>` is the method name declared in `# Interfaces`.
2. `service.<method>.side_effect = <ExceptionClass>(...)` — the service raises, and the router maps it to an HTTP status. The exception class comes from `# Interfaces` — the same class the router catches.
3. The return value contains every key the response model declares. A missing key fails inside Pydantic with `ValidationError`, far from the mock configuration line.
4. Configure only the methods the router calls. An unconfigured method returns `MagicMock()`, which propagates as garbage into the response.

## 4. Act

`# Act` is exactly one `client.<method>(...)` call. Never call the route handler directly, never call the service directly, never call the repository.

## 5. Assert

1. `response.status_code` — always. Assert the exact `status.HTTP_*` value from `# Interfaces`.
2. `response.json()` — when the scenario describes the body. Assert field by field, not `==` on the whole dict unless the contract fixes every key.
3. Service calls — `service.<method>.assert_called_once_with(...)` with the exact arguments the router passes. Three cases for an injected dependency:
   - **The test saved it in a variable** (preferred, see §2) — compare against the variable: `<param>=<variable>`. Identity match, no `ANY`.
   - **The SUT constructs the dependency internally** (the test cannot hold a reference) — `<param>=ANY` with `from unittest.mock import ANY` at the top of the function. `ANY` is the escape hatch for this case only.
   - **`mock.ANY` or `mock.MagicMock` — always a defect.** `mock` is not a name; the reference is unresolved or the import fails.
4. `service.<method>.assert_not_called()` — the handler rejected the request before calling the service.
5. For request validation errors (missing field, wrong type), the response is `422` from FastAPI before the handler runs — `service.<method>.assert_not_called()`.

## 6. Exception mapping

1. Configure `service.<method>.side_effect = <ExceptionClass>(...)` with the exception class from `# Interfaces`, before the act step.
2. Assert the status code the router maps the exception to. **The mapping comes from `# Interfaces`, not from this skill.** If `# Interfaces` does not name the status code for an exception, do not guess — assert only what the contract names, or return `GAP: mapping for <ExceptionClass> is not specified`.
3. Do not assert on the response's detail text unless `# Interfaces` names the message string. The format of `detail` is the router's choice, not the contract's.
4. After the assert, `service.<method>.assert_called_once()` — the service was called, the mapping happened.

## 7. Assert only what the contract specifies

1. If `# Interfaces` names only the status code, assert the status code. Do not assert on `response.json()["detail"]` text.
2. If `# Interfaces` specifies the response body fields, assert those fields. Do not assert on extra keys the contract does not name.
3. If the test fails on a field the contract does not name, the test is wrong. Remove the assertion — do not change the router.
4. The router is fixed only when it violates `# Interfaces`. A test that demands behaviour the contract does not name is a test defect.

## 8. No real I/O

1. No `sqlite3.connect`, no migrations, no `PRAGMA` — the service is mocked, storage is irrelevant.
2. No `lifespan`, no module-level `app`, no shared client.
3. No filesystem access.
4. No import of a concrete repository, service, or database class. The router test imports only the router factory and the names declared in `# Interfaces`.

## 9. Diagnose failures

| Symptom | Cause | Fix |
|---|---|---|
| `NameError: name '<X>' is not defined` | §1 plan omitted a name | Add the import to the block at the top of the function |
| **`NameError: name 'mock' is not defined`** | `mock.ANY` used without `mock` imported — `mock` is not a name in `unittest.mock` | Replace `mock.ANY` with `ANY`, add `from unittest.mock import ANY`. Better: save the dependency in a variable (§2) and compare against it — no `ANY` needed |
| **`ImportError: cannot import name 'mock' from 'unittest.mock'`** | `from unittest.mock import mock` — no such name | Remove `mock` from the import line. Import `ANY`, `MagicMock`, `call` directly |
| **`ImportError: cannot import name '<Name>' from '<module>'`** | `<Name>` not declared in `# Interfaces` for that module | Re-read `# Interfaces` — only the names declared there exist in `# Target` |
| `pytest: ERROR: not found: <file>::<name>` | Test is inside a class | Move to module level |
| `422` instead of the expected status | Request body missing a field the request model requires | Add the field to the request body in the test |
| `AttributeError: 'Mock' object has no attribute '<method>'` | Service mock configured for a method the service contract does not declare | Re-read `# Interfaces` — the method name comes from there |
| `KeyError: '<key>'` inside Pydantic | Service mock return value missing a key the response model declares | Add the key to `service.<method>.return_value` |
| `AssertionError: expected call not found` | Service called with different arguments | Print `service.method_calls`; compare with the router's call site |
| `sqlite3.OperationalError` in a router test | Test opened a real connection | Remove `sqlite3.connect` — the router test mocks the service |
| Status mismatch — actual `<A>` ≠ expected `<B>` | Test expects a status that `# Interfaces` does not map to | Fix the test — the mapping comes from `# Interfaces` |

## Anti-patterns

1. **Module-level imports, module-level app, module-level client** — every import, app, and client lives inside the test function.
2. **`class TestX` wrapper or `unittest.TestCase`** — module-level function only.
3. **Real `sqlite3.connect` or migrations** — the service is mocked; storage is irrelevant.
4. **`lifespan` or module-level `app`** — `app = FastAPI()` fresh per test, no lifecycle.
5. **Importing a concrete repository, service, or database class** — the router test imports only the router factory and the names declared in `# Interfaces`.
6. **Calling the route handler directly** — go through `client.<method>(...)`.
7. **Calling the service directly** — assert the HTTP surface, not the service surface.
8. **Asserting on `detail` text the contract does not name** — assert the status code only.
9. **Sharing the app or client across tests** — fresh per test.
10. **Missing `import pytest` when the body calls `pytest.raises`** — the import is local, one per function.
11. **`mock.ANY`, `mock.MagicMock`, `from unittest.mock import mock`** — `mock` is the module name, not a name inside `unittest.mock`. Import `ANY`, `MagicMock`, `call` directly. `mock.X` is always unresolved or fails at import.
12. **Inline value passed to the factory** — `<factory>(service, <inline value>)` — the test has no reference to compare in `assert_called_once_with` and reaches for `ANY`. Save the dependency in a variable: `<dep> = <value>`; pass `<dep>` to the factory and to the assertion.
13. **`ANY` for a dependency the test created** — if the test built the dependency, compare by identity. `ANY` is only for dependencies the SUT constructs and the test cannot reference.
14. **Unused imports** — any imported name that the body never references. Every imported name appears in the body.
15. **Guessing the exception-to-status mapping** — if `# Interfaces` does not name the status for an exception, return `GAP: mapping for <ExceptionClass> is not specified` instead of inventing one.