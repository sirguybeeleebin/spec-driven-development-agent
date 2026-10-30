# Repomap

A compressed catalog of the project that the researcher and the implementer receive as `# Context map`.

[← back to README](../README.md)

## What it is

A skeleton of the whole project: every module that has at least one symbol appears under its relative path, and inside each module every class, method, function, and typed field appears with its signature, its docstring, and nothing else. Bodies are replaced by `...`. Module docstrings are rendered first. Signatures and docstrings keep their original line breaks.

Built once per task, during the `RESEARCH` phase, and stored on `state.context_map`. Only the researcher and the implementer render it in their user message. The tester and the fixer do not see it.

## Why it exists

An agent that writes or tests one file needs to know what the rest of the project provides: module paths, exported symbols, signature shapes — without paying the token cost of the whole source. The map is a bounded answer: it is ranked against the task's own interfaces and truncated at `max_tokens`.

## What it looks like

For a task whose target is `repositories/products.py`:

````text
repositories/products.py:
│"""Products repository over the products table."""

│class ProductRepository:
│    """Read/write access to the products table.

│    Description:
│        Repository for the products table.
│    """

│    def get(self, product_id: str) -> dict | None:
│        """Return the product with the given id, or None."""
⋮...
│    def insert(
│        self,
│        product_id: str,
│        name: str,
│    ) -> None:
│        """Insert one product row."""
````

- **`path:`** — one header per module.
- **`│`** on every line of the body.
- **`indent`** after `│` — `4 × depth` in `scope`, so methods sit one level deeper than their class, and class fields sit with methods.
- **`docstring`** — one level deeper than its header, quotes included, verbatim line breaks preserved.
- **`⋮...`** — a single separator line between two blocks whose source lines are not adjacent. Never inside a block.
- **`module_docstring`** — rendered first, at zero indent, before any block.

Modules are separated by a blank line. Within a module, blocks are sorted by source line. The whole block is truncated at `max_tokens × 4` characters; whatever does not fit is dropped, lowest-ranked first.

## How it is built

1. Scan `root` recursively. For every file whose suffix is in `parser.extensions`, call `parser.extract(path.read_bytes())` and group the returned tags by relative path.
2. Turn definitions (`kind` in `class`, `function`, `field`) into graph nodes keyed by `path::scope::name`. Turn references (`kind = "ref"`) into edges from the caller to every definition with a matching `name`.
3. Seed nodes: for each interface block in the focused task, run `parser.extract` on its content and collect the top-level `class` and `function` names; then keep the definition in the task's target path whose name matches a seed. Focus task is the one named by `state.current_step.task_id`, or `tasks[0]` when there is no current step.
4. Score nodes with personalized PageRank (damping `0.85`, 30 iterations), prior concentrated on the seed set.
5. Rank nodes by score; add nodes to the selected set while total estimated characters stay under the budget. Group the selected nodes by file; order files by the maximum score in each; render.

## Parser interface

```python
class Parser(Protocol):
    @property
    def extensions(self) -> frozenset[str]: ...

    def extract(self, source: bytes) -> list[Tag]: ...
```

`extract` returns typed tags — no AST escapes to the engine. The default is `PythonParser` on **tree-sitter**, which tolerates half-written files; a different language is a different `Parser` and the rest of the map is unchanged.

## `Tag`

```python
@dataclass(frozen=True)
class Tag:
    name: str
    kind: str
    scope: tuple[str, ...] = ()
    header: str = ""
    docstring: str = ""
    line: int = -1
    caller: str | None = None
```

- `kind` is one of `module_docstring`, `class`, `function`, `field`, `ref`.
- `scope` is the nesting path from the module (`("ProductRepository",)` for a method).
- `header` is the source text of the signature up to the colon.
- `docstring` is the cleaned docstring of the symbol (empty for `field` and `ref`).
- `line` is the start line in the source (or `-1` for a reference).
- `caller` is the `::`-joined scope of the caller for a reference; `None` otherwise.

[← back to README](../README.md)