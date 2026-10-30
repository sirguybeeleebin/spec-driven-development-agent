---
name: implementing-business-logic
description: Implements a service class that orchestrates collaborators through contracts the task already declares, without importing their concrete implementations. Use when the target is a service, use case, or orchestration layer whose dependencies are typed as Protocol or declared as interfaces in the task, and whose body must call only those contracts; or when the target must stay decoupled from a specific storage, HTTP, or messaging implementation so it can be tested with substitutes.
license: MIT
compatibility: python>=3.10
metadata:
  layer: reference
  domain: application
---

# Implementing business logic

## When to use

1. The target is a service class that receives collaborators through its constructor.
2. The task already declares contracts for those collaborators (`Protocol`, `ABC`, or interface stubs) in `# Interfaces`.
3. The service must call only the operations those contracts name, not concrete repository, client, or ORM classes.
4. The test layer will substitute the collaborators with fakes — the service must be constructible without a real database, HTTP client, or filesystem.

## When NOT to use

1. The target is itself a repository, client, or adapter — it implements a contract; it does not consume one.
2. The task declares no contracts and the target must call a concrete class directly — that is a wiring defect, report `GAP: no contract declared for <collaborator>`.
3. The target is a router — it translates HTTP to service calls; routers import services, not contracts.

## 1. Contracts come from `# Interfaces`

1. `# Interfaces` in the user message is the complete and only source of truth for the contracts the target consumes and declares.
2. For every symbol in `# Interfaces`, record: name, methods, parameter names, return types, exceptions named in `Raises:`.
3. For each collaborator the target receives through its constructor, its contract is already in `# Interfaces` or `# Context map`. If it is not in either, stop and return `GAP: contract for <collaborator> not declared`. Do not invent one.
4. Do not open the task file, the migration directory, or any other file to look for a contract. If `# Interfaces` does not declare it, it does not exist for the target.

## 2. Program against contracts, not implementations

1. **The service imports only:**
   - its own declared contracts (`Protocol`, `ABC`, or interface types),
   - the standard library,
   - nothing else.

2. **The service never imports:**
   - `repositories.*`, `clients.*`, `models.*` (ORM), `db.*`,
   - `sqlite3`, `psycopg`, `httpx`, `requests`, any driver,
   - a concrete class that happens to satisfy a contract.

3. **If `# Interfaces` declares a `Protocol` named `OrderRepository`, the service types its constructor parameter as that `Protocol`.** It does not import `repositories.orders.OrderRepository` — that is a different symbol with a different module path, and importing it couples the service to storage.

4. **If `# Interfaces` declares the contracts in the service's own module**, the service does not re-declare them. It references them by name. Re-declaring a `Protocol` that `# Interfaces` already gives is a defect: it shadows the source of truth and drifts from it.

5. **If `# Interfaces` declares the contracts in a separate module**, the service imports from that module by the exact path `# Interfaces` names — never from `repositories/`.

6. **The concrete class is wired at composition time**, by the module that builds the service (an application module, a CLI entry point, a test fixture). The service does not know which concrete class it receives.

## 3. Constructor shape

1. The constructor takes every collaborator as a keyword or positional argument.
2. Each parameter is typed as its contract, not as `Any` and not as a concrete class.
3. The constructor body stores each parameter on `self`. No I/O, no connection, no side effect.
4. The constructor does not instantiate a collaborator. If the service creates its own dependency, it is not injectable and cannot be tested with substitutes — that is a defect.

```python
class CheckoutService:
    def __init__(
        self,
        products: ProductRepository,
        orders: OrderRepository,
        lines: OrderLineRepository,
    ) -> None:
        self.products = products
        self.orders = orders
        self.lines = lines
```

`ProductRepository` here is the `Protocol` from `# Interfaces`, not `repositories.products.ProductRepository`.

## 4. Method bodies call only the contract

1. Every call on a collaborator uses a method named in that collaborator's contract. A call to a method the contract does not declare is a defect — either the contract is wrong or the call belongs elsewhere.
2. The service does not inspect a collaborator's private attributes, call `_`-prefixed methods, or reach into its internals.
3. The service does not assume a return shape the contract does not name. If the contract says `dict | None`, the service branches on `None` and reads named keys; it does not assume extra keys.
4. The service does not translate a collaborator's exception into a different type unless `# Interfaces` says it does. If the contract says the collaborator raises `KeyError`, the service either lets it propagate or catches that exact class.
5. The service does not open, commit, or roll back a transaction. It does not call `commit` on a collaborator. Transaction control belongs to the layer that owns the connection — usually the composition root, or the contract itself if it exposes a unit-of-work method.

## 5. Validate before writing

1. Run every validation the scenario names **before** calling any collaborator that writes.
2. An invalid input must fail with no collaborator side effect. Assert this in the test, and arrange the body so it holds: pure checks first, writes second.
3. Validation reads from contracts that only look up state (e.g. `get`) — never from a contract method that mutates.
4. A validation error names the offending value (`f"Product {product_id} not found"`), not a generic message. The service is the only place that knows what the value means.

## 6. Order of writes

1. Write the parent row before the child rows, when the contract implies a dependency. The service is the only place that knows the domain order, so it is the service's job to sequence the calls.
2. If a write fails mid-sequence, the service does not attempt compensation unless `# Interfaces` describes a compensating call. Let the exception propagate; the transaction boundary at the composition root handles rollback.
3. Return the value the scenario's `Returns:` describes, built from reads that follow the writes — or from the values the service already holds, if the scenario allows. Do not invent a return value the contract does not name.

## 7. No ambient state

1. The service does not call `datetime.now()`, `time.time()`, `random.*`, `uuid.uuid4()`, `os.urandom`, or any ambient source.
2. If the scenario needs a value from ambient state, `# Interfaces` declares it as an injected argument (`clock: Callable[[], str]`). Use the injected argument, not the global.
3. If `# Interfaces` declares no injected source for a value the scenario needs, stop and return `GAP: no injected source for <value>`. Do not fall back to a global.

## 8. No I/O in the service

1. The service does not open a database connection, an HTTP client, a socket, or a file.
2. The service does not read environment variables.
3. The service does not print or log through `logging`, `warnings`, or `sys.stderr`. Tracing is the only exception — see `# Constitution` `# Tracing`.
4. The service does not sleep, retry with backoff, or schedule work. Scheduling belongs to the layer that owns the runtime.

## 9. Traces and comments

1. Every method with a non-empty body starts with a trace line per `# Constitution` `# Tracing`.
2. Every call on a collaborator that has a side effect (a write) is preceded by its own trace line.
3. Every logical block is preceded by a comment that answers **why**, not **what**.

## 10. Diagnose failures

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: cannot import name 'OrderRepository' from 'repositories.orders'` | Service imported the concrete module instead of the declared contract | Remove the import; type the parameter as the contract from `# Interfaces` |
| `TypeError: __init__() missing N required positional arguments` | Constructor signature does not match the contract | Match the signature from `# Interfaces` exactly |
| `AttributeError: 'FakeX' object has no attribute '<method>'` | Service called a method the contract does not declare | Re-read the contract in `# Interfaces`; the call belongs elsewhere or the contract is wrong |
| Fake receives a call the test did not expect | Service called a collaborator outside the scenario | Remove the call; only methods the scenario describes are invoked |
| Service opens a real connection in a unit test | Service imported `sqlite3` or a concrete repository | Remove the import; the connection is built by the composition root, not the service |
| `GAP: contract for <collaborator> not declared` | `# Interfaces` declared no contract for a collaborator | Correct return — do not invent a Protocol |

## 11. No-op patches and degenerate loops

1. Before calling `patch`, verify `search != replace`. Identical strings mean nothing is being fixed.
2. After `patch`, verify with `bash: grep -n "<expected_new_line>" <path>`. If not found, the patch was a no-op — re-read the file and rebuild the search string.
3. If the previous action produced no state change, do not repeat it — change the tool, the target, or the hypothesis.
4. Do not emit repeated "I think I should…" text without a tool call. Either call a tool or return `GAP`.

## References

- `# Interfaces` in the user message — the complete and only source of truth for contract names, method signatures, and exception classes. No file lookup is needed.
- `testing-with-mocks` skill — describes how the service will be tested through the same contracts.
- `# Constitution` `# Implementing` — declares that contracts live in the target module; this skill describes how the service consumes them.

## Anti-patterns

1. Importing a concrete repository, client, ORM model, or driver in the service module.
2. Re-declaring a `Protocol` that `# Interfaces` already declares.
3. Typing a constructor parameter as `Any`, `object`, or a concrete class instead of the contract.
4. Instantiation of a collaborator inside the constructor or a method body.
5. Calling a method the contract does not declare.
6. Calling `commit`, `rollback`, `close`, or `begin` on a collaborator.
7. Reading ambient state instead of using an injected argument.
8. Opening a connection, HTTP client, socket, or file inside the service.
9. Performing writes before validation.
10. Running `bash: cat <task_file>.md` or `bash: cat repositories/*.py` to look for a contract — `# Interfaces` already contains every contract the target consumes or declares.
11. `patch` with `search == replace`.
12. Repeating the same no-op action without new information.