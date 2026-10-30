# tools/append.py

from __future__ import annotations

from pathlib import Path


class AppendTool:
    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()

    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "append",
                "description": (
                    "Append content to a file. Creates the file if it "
                    "does not exist. One call writes one block. The "
                    "path must be workspace-relative. If the file "
                    "already exists and does not end with a newline, "
                    "a newline is inserted before the new content so "
                    "blocks never concatenate on one line."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Workspace-relative file path.",
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

    def execute(self, args: dict) -> dict:
        path_value = args.get("path")
        content = args.get("content")
        if not isinstance(path_value, str) or not path_value:
            return {
                "ok": False,
                "error": "append: 'path' must be a non-empty string",
            }
        if not isinstance(content, str):
            return {
                "ok": False,
                "error": "append: 'content' must be a string",
            }

        candidate = (self._root / path_value).resolve()
        if not candidate.is_relative_to(self._root):
            return {
                "ok": False,
                "error": f"append: path escapes workspace: {path_value!r}",
            }

        candidate.parent.mkdir(parents=True, exist_ok=True)

        if candidate.suffix == ".py" and candidate.name != "__init__.py":
            init = candidate.parent / "__init__.py"
            if not init.exists():
                init.write_text("", encoding="utf-8")

        if candidate.is_file():
            existing = candidate.read_text(encoding="utf-8")
            if existing and not existing.endswith("\n"):
                content = "\n" + content

        with candidate.open("a", encoding="utf-8") as f:
            f.write(content)

        return {"ok": True, "path": path_value, "chars": len(content)}
