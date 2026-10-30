# tools/patch.py

from __future__ import annotations

from pathlib import Path


class PatchTool:
    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()

    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "patch",
                "description": (
                    "Replace one exact substring in a file. The search "
                    "string must match the file byte-for-byte and must "
                    "occur exactly once. One call replaces one region. "
                    "The path must be workspace-relative."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Workspace-relative file path.",
                        },
                        "search": {
                            "type": "string",
                            "description": "Exact text to replace.",
                        },
                        "replace": {
                            "type": "string",
                            "description": "Text to put in its place.",
                        },
                    },
                    "required": ["path", "search", "replace"],
                },
            },
        }

    def execute(self, args: dict) -> dict:
        path_value = args.get("path")
        search = args.get("search")
        replace = args.get("replace")
        if not isinstance(path_value, str) or not path_value:
            return {
                "ok": False,
                "error": "patch: 'path' must be a non-empty string",
            }
        if not isinstance(search, str) or not search:
            return {
                "ok": False,
                "error": "patch: 'search' must be a non-empty string",
            }
        if not isinstance(replace, str):
            return {
                "ok": False,
                "error": "patch: 'replace' must be a string",
            }

        candidate = (self._root / path_value).resolve()
        if not candidate.is_relative_to(self._root):
            return {
                "ok": False,
                "error": f"patch: path escapes workspace: {path_value!r}",
            }
        if not candidate.is_file():
            return {
                "ok": False,
                "error": f"patch: file not found: {path_value!r}",
            }

        original = candidate.read_text(encoding="utf-8")
        occurrences = original.count(search)
        if occurrences == 0:
            return {
                "ok": False,
                "error": f"patch: search not found in {path_value}",
            }
        if occurrences > 1:
            return {
                "ok": False,
                "error": (
                    f"patch: search appears {occurrences} times in "
                    f"{path_value}; anchor must be unique"
                ),
            }

        updated = original.replace(search, replace, 1)
        candidate.write_text(updated, encoding="utf-8")

        if candidate.suffix == ".py" and candidate.name != "__init__.py":
            init = candidate.parent / "__init__.py"
            if not init.exists():
                init.write_text("", encoding="utf-8")

        return {"ok": True, "path": path_value, "chars": len(updated)}
