---
name: testing-with-mocks
description: Tests the business logic. The target is a service, use case, or orchestration layer; its collaborators are injected through the constructor and replaced with MagicMock. Use when the test must control collaborator returns or exceptions, verify call arguments, order, or count, and the test opens no real sqlite3.connect, no TestClient, and no filesystem.
license: MIT
compatibility: python>=3.10, pytest>=8, unittest.mock
metadata:
  layer: reference
  domain: unit-testing
---

# Testing with mocks

## When to use

1. The SUT is a service, use case, or orchestration layer — its job is to call collaborators, not to talk to storage or HTTP.
2. Every collaborator is injected through the constructor or call arguments.
3. The test replaces each collaborator with `MagicMock()` (or a hand-rolled fake) and configures returns or exceptions.
4. The test opens **no** real `sqlite3.connect`, **no** `TestClient`, **no** filesystem.

A test that opens `sqlite3.connect` is not this layer. A test that imports `TestClient` is not this layer. Only the business-logic test belongs here.

## 1. Imports — local, planned, complete

Imports are the first thing you write, and they live **inside** the test function. A module-level import is a defect.

### Why local, not module-level

1. The test file grows by `append`: each scenario is a separate `def test_<behavior>()` added by a separate `append` call. A module-level import block belongs to the first scenario only. The second scenario cannot re-open the file to add its own imports without duplicating the block or editing the first test.
2. The tester has no `patch` and no `read`. A broken module-level import fails collection for **every** test in the file. A broken local import fails only its own test — the rest keep working. An import omitted entirely from a local block cannot be fixed in place at all.
3. Local imports make each test self-contained. A test that reads top-to-bottom has no hidden dependency on a block above it.

### Plan the body in reasoning first

Before writing any code, write the skeleton as plain text:

```
# Given: <what setup runs>
# When: <the single SUT call>
# Then: <assertions, and whether any use pytest.raises or call assertions>
```

Mark explicitly whether `Then` uses `pytest.raises` and which calls it asserts. The plan is not code — one sentence per section.

### From the plan, answer four questions

For every "yes", add the import to the block:

| Question | Import |
|---|---|
| Does the body call `pytest.raises(...)`? | `import pytest` |
| Does the body construct `MagicMock(...)` or use `call(...)`? | `from unittest.mock import MagicMock` / `from unittest.mock import MagicMock, call` |
| Does the body reference the SUT class? | `from <module> import <Class>` |
| Does the body name `sqlite3.IntegrityError` inside `pytest.raises(...)`? | `import sqlite3` |

If all four answers are "no", the body is empty — return to planning.

A `pytest` import is required **only** when the body calls `pytest.raises(...)` or `pytest.mark.*`. An unused import is a defect.

### Import order inside the block

stdlib → `pytest` → `unittest.mock` → module under test. One blank line after the block, before `# Given`.

```python
def test_checkout_persists_order_and_lines() -> None:
    from unittest.mock import MagicMock
    from services.checkout import CheckoutService

    # Given
    ...
```

If the test uses `pytest.raises` and order-sensitive `attach_mock`:

```python
def test_checkout_rejects_empty_lines() -> None:
    import pytest
    from unittest.mock import MagicMock, call
    from services.checkout import CheckoutService

    # Given
    ...
```

### Verify before the write

Before the `append`, walk the planned body and list every identifier: classes, functions, modules, constants. Every identifier must appear in the import block or be a Python builtin (`dict`, `list`, `None`, ...). If an identifier is missing, revise the plan — do not `append` until every name is accounted for.

The tester has no `patch` and no `read`. A test appended with a missing import cannot be fixed in place — it fails with `NameError`, and the run moves to the fixer. Prevention is the only way.

## 2. Algorithm — configure mocks before writing the test

Run steps 1–8 before writing `# Given`. Do not skip a step.

1. `bash: cat <sut_module>.py`. Read the SUT in full.
2. For every SUT method the test calls, list every collaborator call it makes, **in order**: collaborator name, method name, arguments, **and the form of each argument** (positional or keyword). The form matters — `assert_called_once_with` matches the call signature, and a positional SUT call does not satisfy a keyword assertion (§6.1).

   Write down the exact form for each call site. Example:

   ```
   orders.insert(order_id, customer_id, "PENDING", created_at)   # 4 positional
   lines.insert(order_id, line["product_id"], line["qty"], ...)  # 5 positional
   ```

   If a call site mixes positional and keyword, record the mix.

3. For every collaborator call, record what the SUT does with the return value:
   - stores it in a local and uses it later (track the local);
   - checks it against `None`;
   - reads named keys `d[k]` — list the keys;
   - iterates it — record the required length;
   - ignores it.
4. For every collaborator call, determine where the return value must come from:
   - the SUT wrote it earlier via another collaborator method (`insert`→`get`, `insert`→`list_by_order`) → the mock's return value must mirror what the SUT wrote;
   - the scenario supplies it → preset from `# Scenarios`;
   - the value is an input to the scenario (e.g. "the product exists") → preset a minimal valid dict with every key from step 3.
5. Configure every mock before `# Act`: `<method>.return_value` for one value, `<method>.side_effect` for an exception or a sequence. Every call from step 2 has a configuration; an unconfigured call returns `MagicMock()`, which propagates as garbage into a later assertion.
6. Verify against `# Scenarios`. Each `Then` line about the SUT's return value must be derivable from step 5. `Then` says "N elements" → step 5 gives N elements. `Then` reads a field → step 5's dict has that field.
7. **For every `Then` line that asserts a collaborator call**, note the assertion form to use in §6: `assert_called_once_with(<args>)` with the **same positional/keyword form as step 2**. If the SUT calls `insert("a", "b")`, the assertion is `assert_called_once_with("a", "b")`. Do not convert to keyword because it reads nicer.
8. Only now write the test.

If step 6 cannot be satisfied, fix step 5 — do not change the SUT. A `Then` failure caused by missing mock configuration is a test defect, not a SUT defect.

If step 7 disagrees with step 2, the assertion is wrong — the SUT is the source of truth for call form. Do not rewrite the SUT to match a prettier assertion.

## 3. Create bare MagicMock — no spec

1. One `MagicMock()` per collaborator. No `spec=`, no `spec_set=`. `MagicMock(spec=Protocol)` is unreliable with `typing.Protocol` — `_mock_methods` is sometimes empty and the first `mock.method(...)` raises `AttributeError`.
2. Never write `class Mock<Name>(Protocol): ...` — a `Protocol` cannot be instantiated.
3. The Protocol from `# Interfaces` is a method list to configure, not a runtime spec.

## 4. Configure returns and exceptions

1. `mock.<method>.return_value = <value>` — normal return.
2. `mock.<method>.side_effect = <ExceptionClass or instance>` — raise on call.
3. `mock.<method>.side_effect = [a, b, c]` — sequential returns.
4. If both are set, `side_effect` wins.
5. Every return value contains every key from step 3 of the algorithm. A return value missing a key the SUT reads fails with `KeyError` inside the SUT, far from the configuration line.

## 5. Test structure

1. Every test is a module-level function `def test_<behavior>() -> None:`. Never wrap in `class` or `unittest.TestCase`.
2. Imports live inside the function — §1.
3. `# Given` — build mocks, apply step 5 of the algorithm, construct the SUT, prepare inputs.
4. `# Act` — exactly one SUT method call.
5. `# Then` — assert the return value field by field; assert calls through `mock.<method>.assert_called_once_with(...)` or `assert_not_called()`. **The assertion must match the SUT's call form exactly** — see §6.
6. Do not open a database connection, start an HTTP client, touch the filesystem, or use `monkeypatch`/`patch`.

## 6. Call assertions — signature, not values

`mock.<method>.assert_called_once_with(...)` compares the **exact call signature**, not just the argument values. `insert("a", "b")` and `insert(x="a", y="b")` are **different calls** for the mock, even when the values match. A test that asserts with keyword arguments against a SUT that calls positionally (or vice versa) fails with `AssertionError: expected call not found`.

### 6.1 Match the SUT's call form

The assertion must reproduce the call **exactly as the SUT writes it**:

```python
# SUT (services/checkout.py):
self.orders.insert(order_id, customer_id, "PENDING", created_at)

# Test — PASSES (positional matches positional):
order_repo.insert.assert_called_once_with(
    "o1", "c1", "PENDING", "2024-01-01T00:00:00+00:00",
)

# Test — FAILS (keyword does not match positional):
order_repo.insert.assert_called_once_with(
    order_id="o1",
    customer_id="c1",
    status="PENDING",
    created_at="2024-01-01T00:00:00+00:00",
)
```

The failure message is:

```
AssertionError: expected call not found.
Expected: insert(order_id='o1', customer_id='c1',
                 status='PENDING', created_at='2024-01-01T00:00:00+00:00')
  Actual: insert('o1', 'c1', 'PENDING', '2024-01-01T00:00:00+00:00')
```

When the SUT mixes positional and keyword, the assertion must mix them the same way.

### 6.2 Algorithm step 2 records the form

When algorithm step 2 lists collaborator calls, **record for each argument whether it is positional or keyword**. `insert(order_id, customer_id, ...)` and `insert(order_id=order_id, customer_id=customer_id, ...)` are different calls, and the test must use the same form.

### 6.3 Discover the actual call when the assertion fails

When `assert_called_once_with` fails, do not guess. Read the actual call:

```python
print(order_repo.insert.call_args)
# call('o1', 'c1', 'PENDING', '2024-01-01T00:00:00+00:00')

print(order_repo.insert.call_args.args)
# ('o1', 'c1', 'PENDING', '2024-01-01T00:00:00+00:00')

print(order_repo.insert.call_args.kwargs)
# {}
```

`call_args` is `None` when the mock was never called. `.args` is the positional tuple, `.kwargs` is the keyword dict. Use this output to write the assertion — copy the form, do not derive it from the source.

`call_args_list` is the list of all calls. `mock.method_calls` is the list of every method call on the mock (`call.insert(...)`, `call.get(...)`).

### 6.4 Assert with exact form, not partial

`assert_called_once_with(...)` requires **every argument** of the call. A SUT that calls `insert("o1", "c1", "PENDING", "ts")` is not satisfied by `assert_called_once_with("o1", "c1")`. To assert only some arguments, unpack manually:

```python
args, kwargs = order_repo.insert.call_args
assert args[0] == "o1"
assert args[1] == "c1"
assert args[2] == "PENDING"
```

But this loses the "called exactly once" guarantee — combine with `assert order_repo.insert.call_count == 1`.

### 6.5 Order across multiple mocks

`assert_called_once_with` on one mock does not check **when** it was called relative to another mock. A scenario "the header is inserted before the lines" needs the cross-mock ordered list:

```python
from unittest.mock import MagicMock, call

parent = MagicMock()
parent.attach_mock(product_repo.get, "get_product")
parent.attach_mock(order_repo.insert, "insert_order")
parent.attach_mock(line_repo.insert, "insert_line")

# ... run SUT ...

assert parent.mock_calls == [
    call.get_product("p1"),
    call.insert_order("o1", "c1", "PENDING", "2024-01-01T00:00:00+00:00"),
    call.insert_line("o1", "p1", 1, "10.00", "USD"),
]
```

`parent.mock_calls` is the ordered list across all attached mocks. It catches: wrong order, missing call, extra call, wrong arguments. This is the only assertion that can verify the header-before-lines invariant — one `assert_called_once_with` per mock cannot.

Same positional-vs-keyword rule applies to `parent.mock_calls` entries.

### 6.6 Count assertions

| Assertion | Meaning |
|---|---|
| `mock.assert_not_called()` | Zero calls |
| `mock.assert_called()` | One or more calls, any args |
| `mock.assert_called_once()` | Exactly one call, any args |
| `mock.assert_called_with(...)` | The **last** call has these args |
| `mock.assert_called_once_with(...)` | **Exactly one** call, these args |
| `mock.assert_any_call(...)` | At least one call has these args |
| `mock.call_count == N` | Exactly N calls |

Use `assert_called_once_with` when the scenario says "the SUT calls it once with these arguments". Use `assert_any_call` when order does not matter and the mock may be called multiple times. Use `assert_called_with` only when there are multiple calls and only the last matters.

### 6.7 What not to do

- Do not print `mock.method_calls` and eyeball it — write an assertion. The test must fail automatically when the SUT changes.
- Do not assert `str(mock.mock_calls) == "..."` — fragile, depends on repr formatting.
- Do not assert `mock.called is True` — always true if any call happened, ignores arguments and count.
- Do not use `assert_called_with` (no `once`) when the scenario requires exactly one call — a SUT that calls twice passes `assert_called_with` if the last call matches.
- Do not use `assert_called_once_with` per mock when the scenario names an **order across mocks** — that assertion cannot see order. Use `attach_mock` + `parent.mock_calls` (§6.5).

## 7. Assert only what the contract specifies

1. If `# Interfaces` names only the exception class in `Raises:`, use `pytest.raises(<ExactClass>)` without `match=`. Do not assert on message text.
2. If `# Interfaces` specifies the message string, use `match=` with that exact substring.
3. If the test fails on `match=` and the contract does not specify the message, the test is wrong. Remove `match=` — do not change the SUT.
4. If the test asserts a call the scenario does not describe, the test is wrong. Remove the assertion.
5. The SUT is fixed only when it violates `# Interfaces`. A test that demands behaviour the contract does not name is a test defect.

## 8. Diagnose failures

| Symptom | Cause | Fix |
|---|---|---|
| `KeyError: '<key>'` inside the SUT | Test data or mock return omits a key the SUT reads | Algorithm step 3; add the key |
| `TypeError: object of type 'NoneType' has no len()` on a result assertion | Read-back mock left at `None` though the SUT wrote through another method | Algorithm step 4; mirror what the SUT wrote |
| `AssertionError: len(<list>) == 0` though the scenario expects N > 0 | Read-back list mock left at `[]` | Algorithm step 4; preset N elements |
| `AssertionError: expected call not found` — `Expected: f(x=...)` / `Actual: f(...)` | Assertion used keyword args; SUT calls positionally (or vice versa) | §6.1 — rewrite the assertion in the SUT's call form. Print `mock.method.call_args` to see the actual form |
| `AssertionError: expected call not found` — same form, different args | Argument value differs (wrong literal, wrong order) | Print `mock.method.call_args`; compare field by field with the SUT's call site |
| Test fails far from `# Act` with a `MagicMock` value in the traceback | Algorithm step 5 was skipped for some collaborator call | Re-run algorithm; configure every call from step 2 |
| `NameError: name 'pytest' is not defined` | §1 question 1 was answered "no" but `pytest.raises` is in the body | Add `import pytest` as the first line of the function |
| `NameError: name 'MagicMock' is not defined` | §1 question 2 was answered "no" but `MagicMock(...)` is in the body | Add `from unittest.mock import MagicMock` |
| `NameError: name 'call' is not defined` | Body uses `call(...)` in `parent.mock_calls` without importing it | Add `from unittest.mock import MagicMock, call` |
| `TypeError: Protocols cannot be instantiated` | Test wrote `class MockX(Protocol): ...` | Delete the class; use `MagicMock()` |
| `AssertionError: Regex pattern did not match` | `match=` on a message the contract does not specify | Remove `match=`; assert the exception class (§7) |
| `sqlite3.OperationalError` in a unit test | Test opened a real connection | Remove `sqlite3.connect` and any migrations loop — a real connection means the test is not exercising business logic |
| `AssertionError: expected call not found` on a mock that should have been called | Wrong mock instance — two `MagicMock()` for the same collaborator | One `MagicMock()` per collaborator; pass the same instance to the SUT and to the assertion |

## Anti-patterns

1. **Module-level imports.** Every import must be inside the test function. A module-level `from unittest.mock import MagicMock` at the top of the file belongs to the first test only; the second test cannot add its own imports without duplication. Import locally (§1).
2. `class TestX` wrapper or `unittest.TestCase`.
3. `MagicMock` for the whole collaborator without configuring every call from algorithm step 2.
4. `monkeypatch` or `patch` on a module attribute when the constructor already accepts the dependency.
5. Importing a concrete collaborator implementation in a unit test.
6. `mock.get.return_value = None` when the SUT reads back its own write — configure it to mirror the persisted state.
7. `match=` on a message the contract does not specify.
8. Asserting a call the scenario does not describe.
9. `sqlite3.connect`, `TestClient`, or filesystem access inside the test body.
10. Opening a real connection or importing `TestClient` in this test — the test is then exercising a different layer, not business logic.
11. **`import pytest` when the body does not call `pytest.raises(...)`.** An unused import is a defect — §1 question 1 was answered "yes" but the body has no `pytest.raises`.
12. **`assert_called_once_with` with keyword arguments when the SUT calls positionally (or vice versa).** `insert(order_id="o1", ...)` and `insert("o1", ...)` are different calls for the mock. §6.1 — match the SUT's form exactly.
13. **Verifying cross-mock order by listing `assert_called_once_with` per mock.** That assertion cannot see order — a SUT that calls lines-before-header passes it. Use `attach_mock` + `parent.mock_calls` (§6.5).
14. **Asserting calls without checking count.** `assert_called_with` (no `once`) passes when the SUT calls twice and the last call matches. Use `assert_called_once_with` for the "exactly once" contract.