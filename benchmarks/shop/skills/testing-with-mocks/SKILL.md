---
name: testing-with-mocks
description: Tests a service class whose Protocol-typed collaborators arrive through `__init__`, replacing each with a test double and asserting orchestration, validation, and result assembly without a real database or HTTP endpoint. Use when the target test exercises a service class that consumes Protocol-typed collaborators through `__init__`.
version: 1.2.0
tags:
  - testing
  - mocks
  - pytest
  - service
  - python
license: MIT
compatibility: Python 3.10+, pytest 8+, unittest.mock
---

# Testing with Mocks

This skill helps write one pytest function per Gherkin scenario. Every collaborator the SUT receives through `__init__` becomes a test double. The interface says what the SUT does; the SUT source says when; the doubles mirror the SUT's execution path for this one scenario.

## When to Use

Use this skill when the target test exercises a service class that:
- receives collaborators through `__init__`;
- types those collaborators as Protocol, ABC, or abstract class;
- sequences collaborator calls, validates inputs, or assembles a result.

## How to Work

1. **Read the target test file.** Run `read` on `# Target test file`. Record test functions already present. If `# Test function` is already there — go to Verify.
2. **Read the SUT source.** Run `read` on `# Target file`. Record the `__init__` parameter names and types, the method body under test, every raise, every collaborator call, the return shape. For every collaborator call, record the exact argument style — positional or keyword — and the exact order. If a parameter is typed `sqlite3.Connection`, a file handle, or an HTTP client — this is not a mocks test, stop and report `- [ ] <scenario name> — wrong skill, SUT uses real resources`. If the file is missing, report `- [ ] <scenario name> — SUT file missing` and stop.
3. **Build the plan.** Read `# Interfaces`, `# Declares`, `# Gherkin`, `# Implementer summary`. Cross-check against the source — the source wins. Classify the scenario: happy path (keywords *returns*, *creates*, *persists*, *succeeds*) or raise path (keywords *raises*, *rejects*, *invalid*, *empty*, *missing*, *duplicate*, *storage*). For a raise path record the exact `Raises:` class. For each `__init__` parameter record its role on the execution path: **Before** — called above the raise, must return a concrete value; **At** — called on the raise line, or the validation check that raises without any collaborator call; **After** — called below the raise, skipped on the failing path.
4. **Write the test.** One `append` on `# Target test file` with one test function. Follow the `## Imports` section exactly — two imports on a happy path, four on a raise path.
5. **Verify.** Run `read` on `# Target test file`. Function name present exactly once. Every `Then` step from `# Gherkin` has a matching assertion. On a raise path, `import pytest` is present. Every `assert_called_once_with` matches the SUT call style recorded in step 2. On failure — one `patch`, then one `read`.

## Imports

Every import goes inside the test function, four-space indent, before the first executable statement. No module-level imports.

**Happy path** — the test calls the SUT and asserts on the result. Import exactly two lines:

```python
from unittest.mock import MagicMock
from <sut module> import <SutClass>
```

**Raise path** — the test wraps the SUT call in `pytest.raises(...)`. Import exactly four lines:

```python
from unittest.mock import MagicMock
import pytest
from <sut module> import <SutClass>
from <sut module> import <ExactClass>
```

`import pytest` and `from <sut module> import <ExactClass>` are only present on a raise path. On a happy path they are absent — `pytest` has nothing to do when no exception is expected.

`sut module` is the module path of the SUT class — for `services/checkout.py` the module is `services.checkout`. `<ExactClass>` is the exception class from `Raises:` recorded in step 3.

## Rules

1. **Imports.** Per the `## Imports` section. No module-level imports. `import pytest` on a raise path, absent on a happy path.
2. **One double per parameter.** One `MagicMock()` per `__init__` parameter. Variable name equals the parameter name. Construct the SUT with keyword arguments: `sut = <SutClass>(<param_a>=<param_a>, <param_b>=<param_b>)`.
3. **Before doubles return concrete values** the SUT reads — `int`, `str`, `True`/`False`, `[]`, `[{...}]`, `None`. A bare double fails with `TypeError: '>' not supported between 'int' and 'MagicMock'` when the SUT calls `len()`, compares numerically, or compares a string.
4. **At double configuration by scenario** — missing entity: `return_value = None`; empty collection: `return_value = []`; storage rejection: `side_effect = Exception("<message>")`; duplicate detection with two lookups: `side_effect = [<value>, <value>]`; happy path fixed: `return_value = <value>`; happy path per-call: `side_effect = [<value_1>, <value_2>]`.
5. **Never configure After doubles.** If the SUT reaches an unconfigured After double — that is a SUT bug, and the test surfaces it.
6. **Never set both `return_value` and `side_effect`** on the same method. One or the other. `return_value` masks `side_effect` and `call_count` becomes `0`.
7. **Happy path.** `result = sut.<method>(<args>)`, then `assert len(result) == <N>` where `<N>` equals the number of `Returns:` keys, then `assert result["<key>"] == <expected>` per key. For a value the SUT produces internally (`datetime.now`, UUID, id), assert `result["<key>"] is not None` and `isinstance(result["<key>"], <type>)`. Never hardcode the internally produced value — the SUT and the test would compute different values.
8. **Raise path.** All setup above the `with`, then `with pytest.raises(<ExactClass>): sut.<method>(<args>)`. Only the SUT call inside `with`. Assert `exc_info.value.__cause__ is not None` when the SUT wraps with `raise <StorageError>(...) from exc`; assert `is None` when the SUT raises directly.
9. **Assert collaborator calls.** Before composing `assert_called_once_with`, open the SUT source from step 2 and find the exact collaborator call. Copy its argument style verbatim — positional or keyword — and its argument order into the assertion. `insert("o1", "c1")` and `insert(order_id="o1", customer_id="c1")` are two different calls for `unittest.mock.assert_called_once_with`; the assertion must match the SUT, not the interface signature. After a raise, call `assert_not_called()` on every After collaborator. Call `assert_called_once_with(<exact args>)` on every Before collaborator. For a collaborator called more than once with the same arguments, use `assert <collab>.<method>.call_count == <N>` instead of `assert_called_once_with`.
10. **No `try/except`.** The test expects either a return or a raise, not both.
11. **No extras.** No comments, no `print`, no `pytest.mark`, no `@pytest.fixture`. Each test creates its own doubles.

## Output Format

Return only the test function code. No comments beyond what the Python syntax requires.

## Errors

| Symptom | Cause |
|---|---|
| `NameError: name 'pytest' is not defined` | raise path without `import pytest` — the `## Imports` section for a raise path lists four imports, not two |
| `NameError: name '<ExactClass>' is not defined` | raise path without `from <sut module> import <ExactClass>` |
| `NameError: name 'MagicMock' is not defined` | missing `from unittest.mock import MagicMock` inside the function |
| `NameError: name '<SutClass>' is not defined` | missing `from <sut module> import <SutClass>` inside the function |
| `TypeError: '>' not supported between 'int' and 'MagicMock'` | compared field is a bare double — set a concrete value |
| `TypeError: object of type 'MagicMock' has no len()` | collection double returned a bare double — return `[]` or `[{...}]` |
| `AssertionError: '<timestamp A>' == '<timestamp B>'` on an internally produced field | the test hardcodes a value the SUT produces internally — replace with `is not None` / `isinstance` |
| `AssertionError: expected call not found` with the same argument count, positional vs keyword difference (`Expected: insert(order_id='o1', …)` vs `Actual: insert('o1', …)`) | the test asserts keyword arguments but the SUT calls positionally, or vice versa — copy the SUT call style verbatim into `assert_called_once_with` per Rule 9 |
| `AssertionError: Expected '<method_name>' to be called once. Called 0 times.` | the SUT raises before the call — use `assert_not_called()` instead |
| `AssertionError: Expected '<method_name>' to not have been called` | the SUT calls the method before the raise — remove the `assert_not_called` |
| `Failed: DID NOT RAISE` on a missing-entity scenario | the At double returned a bare double instead of `None` — set `return_value = None` |
| `Failed: DID NOT RAISE <class 'X'>` where the SUT raises a different class | wrong exception class from `Raises:` — check the scenario keywords against the `Raises:` list |
| `AssertionError: assert 1 == 0` on `call_count` | both `return_value` and `side_effect` set — pick one |
| `TypeError: <SutClass>.__init__() missing 1 required positional argument` | a collaborator was not passed — pass every parameter by keyword |
| `AssertionError: Calls not found` from `assert_has_calls` | argument shape wrong (positional vs keyword) — inspect `call_args_list` and match the SUT call style |