# tools/read.py

from __future__ import annotations

from pathlib import Path


class ReadTool:
    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()

    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "read",
                "description": (
                    "Read a file from the workspace. Returns the full "
                    "content. The path must be workspace-relative."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Workspace-relative file path.",
                        },
                    },
                    "required": ["path"],
                },
            },
        }

    def execute(self, args: dict) -> dict:
        path_value = args.get("path")
        if not isinstance(path_value, str) or not path_value:
            return {
                "ok": False,
                "error": "read: 'path' must be a non-empty string",
            }

        candidate = (self._root / path_value).resolve()
        if not candidate.is_relative_to(self._root):
            return {
                "ok": False,
                "error": f"read: path escapes workspace: {path_value!r}",
            }
        if not candidate.is_file():
            return {
                "ok": False,
                "error": f"read: file not found: {path_value!r}",
            }

        content = candidate.read_text(encoding="utf-8")
        return {"ok": True, "path": path_value, "content": content}
