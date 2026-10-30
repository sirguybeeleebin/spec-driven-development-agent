---
name: service-implementing
description: Implements a service-layer class that receives collaborator protocols through `__init__`, validates inputs, sequences collaborator calls, and returns a result dict. Use when the target implements a business operation that coordinates two or more collaborators and produces a result the caller returns.
version: 1.1.0
tags:
  - service
  - orchestration
  - protocols
  - python
license: MIT
compatibility: Python 3.10+
---

# Service Implementing

This skill helps write one file that declares collaborator protocols, an exception hierarchy, and a service class. The service receives collaborators through `__init__`, validates inputs, sequences collaborator calls, returns a result dict. The service owns logic; collaborators own I/O.

## When to Use

Use this skill when the target implements a business operation that:
- receives two or more collaborators through `__init__`;
- types those collaborators as Protocol, ABC, or abstract class;
- validates inputs, sequences collaborator calls, or assembles a result dict.

## How to Work

1. **Read the target file.** Run `read` on `# Target file`. Record top-level classes already present. If the file is missing, every `# Declares` name is pending.
2. **Study the interface.** Read `# Interfaces`. For every name in `# Declares` record: type (exception base, exception subclass, protocol, service class), constructor signature, every method's `Steps:` / `Returns:` / `Raises:`. The exception base is the one nothing extends.
3. **Study the sequence.** Read `# Sequence`. For every arrow from the service to a collaborator record: callee, method, arguments, and phase — `validate`, `produce`, `persist`, or `assemble`. Every `Note over S` is a service step without a collaborator call. If `# Sequence` is `_(none)_`, the service performs only validation and result assembly.
4. **Write the components.** One `append` per pending name, in this order: exception base → exception subclasses → protocols → service. First `append` carries the import block. Method body phases in order: validate → produce → persist → assemble.
5. **Verify.** Run `read` on `# Target file`. Every `# Declares` name is present exactly once. Every persist call is wrapped in `try/except Exception as exc: raise <StorageError>(...) from exc`. Every `Returns:` key appears in the return dict.

## Imports

`from __future__ import annotations` always. `from datetime import datetime, timezone` only when a method body calls `datetime.now(...)`. `from typing import Protocol` only when `# Declares` contains a protocol.

## Rules

1. **Exception base.** `class <Base>(Exception): ...` — body is `...`.
2. **Exception subclass.** `class <Sub>(<Base>): ...` — body is `...`. Base is the exception base from step 2.
3. **Protocol.** `class <Collaborator>(Protocol):` followed by one `def` per `# Interfaces` method with `...` as the body. Signatures copied verbatim.
4. **Service `__init__`.** One parameter per collaborator, type is the protocol. Body stores every parameter as `self._<param> = <param>`.
5. **Service method body — four phases in order:**
   - **validate** — `if <invalid>: raise <ValidationError>("<reason>")` for every `Raise X when Y` in `Steps:`, plus any collaborator lookup the validation needs (`self._<collab>.<get>(...)`).
   - **produce** — `<value> = datetime.now(timezone.utc).isoformat()` or any internally generated value from `Steps:`.
   - **persist** — one `self._<collab>.<method>(<args>)` call per `# Sequence` arrow, in diagram order, each wrapped in `try: ... except Exception as exc: raise <StorageError>("<reason>") from exc`. A `loop` in the diagram becomes a `for` around the try/except. An `alt` becomes an `if` around the try/except.
   - **assemble** — `return { ... }` with exactly one key per `Returns:` key, in `Returns:` order.
6. **Catch the specific `<StorageError>`**, not `<Base>`. If `Raises:` names both, catch the subclass.
7. **Declare, do not import.** Every name in `# Declares` is declared here. Only `# Raises:` classes that the researcher marked `import from <path>` are imported.
8. **No extra code.** Every top-level name in the file is either a `# Declares` name or an import from the `## Imports` section. No helpers, no constants, no type aliases, no `if __name__ == "__main__"`, no `print`.

## Output Format

Return only the file code. No comments beyond what the Python syntax requires.

## Errors

| Symptom | Cause |
|---|---|
| `ImportError: cannot import name '<Name>' from partially initialized module` | a `# Declares` name is imported from its own module — declare it locally per Rule 7 |
| `NameError: name '<Collaborator>' is not defined` in `__init__` | protocol declared after the service — reorder appends, protocol first |
| `NameError: name '<ValidationError>' is not defined` in a method | exception class declared after the service — reorder appends |
| `sqlite3.IntegrityError` escapes to the caller | persist call is not wrapped — wrap in `try/except Exception as exc: raise <StorageError>(...) from exc` |
| `DID NOT RAISE <ValidationError>` | validate phase runs after the persist call — move `if <invalid>: raise` above the first persist |
| `KeyError: '<key>'` from the caller | return dict misses a key from `Returns:` — add it |
| `AttributeError: 'NoneType' object has no attribute '<method>'` | a collaborator was passed as `None` — the composition root passes real instances |
| `TypeError: <Service>() missing 1 required positional argument` | constructor parameter omitted — every `# Interfaces` collaborator is a parameter |