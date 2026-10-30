# tools/read.py

from __future__ import annotations

from pathlib import Path


class ReadTool:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "read",
                "description": "Read the full contents of a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Workspace-relative path to the file.",
                        },
                    },
                    "required": ["path"],
                },
            },
        }

    def execute(self, args: dict) -> dict:
        relative = args["path"]
        path = self._root / relative
        if not path.exists():
            raise ValueError(f"read: file not found: {relative}")
        content = path.read_text(encoding="utf-8")
        print(
            f"[tools.read] path={relative} chars={len(content)}",
            flush=True,
        )
        return {"path": relative, "content": content}
