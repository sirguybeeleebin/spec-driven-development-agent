# Tools

| Tool | Description | Args | Returns | Raises |
|---|---|---|---|---|
| `read` | Read a UTF-8 file under the workspace root. | `path` | `{"path": str, "content": str}` | `ValueError` (file not found), `OSError` (path is a directory) |
| `append` | Append UTF-8 content to a file, creating it and its parent directories if missing. | `path`, `content` | `{"ok": True, "path": str}` | — |
| `patch` | Replace exactly one occurrence of `search` with `replace` in an existing UTF-8 file. | `path`, `search`, `replace` | `{"ok": True, "path": str}` | `ValueError` (file not found / search not found / search ambiguous — more than one match) |
| `load_skill` | Return one skill from the pre-built list of allowed skills. | `title` | `{"name": str, "description": str, "content": str}` | `KeyError` (unknown skill) |