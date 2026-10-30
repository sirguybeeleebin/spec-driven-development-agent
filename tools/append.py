# tools/append.py

from __future__ import annotations

from pathlib import Path
from typing import Any


class AppendTool:
    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()

    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "append",
                "description": (
                    "Append content to a file, creating parent "
                    "directories if needed. A newline is inserted "
                    "between the existing content and the new "
                    "content when needed, so concatenation is "
                    "always syntactically safe."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": ("Workspace-relative file path."),
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to append.",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        }

    def execute(self, args: dict[str, Any]) -> dict:
        path_str = args.get("path")
        content = args.get("content")
        if not isinstance(path_str, str):
            raise ValueError(f"append: 'path' must be a string, got {path_str!r}")
        if not isinstance(content, str):
            raise ValueError(f"append: 'content' must be a string, got {content!r}")

        path = self._root / path_str
        path.parent.mkdir(parents=True, exist_ok=True)

        existing = path.read_text(encoding="utf-8") if path.exists() else ""

        if existing and not existing.endswith("\n"):
            content = "\n" + content
        if content and not content.endswith("\n"):
            content = content + "\n"

        path.write_text(existing + content, encoding="utf-8")
        print(
            f"[tools.append] path={path_str} chars={len(content)}",
            flush=True,
        )
        return {"ok": True, "path": path_str, "chars": len(content)}
