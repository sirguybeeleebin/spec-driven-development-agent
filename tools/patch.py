# tools/patch.py

from __future__ import annotations

from pathlib import Path


class PatchTool:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "patch",
                "description": (
                    "Replace exactly one occurrence of `search` with "
                    "`replace` in an existing file. Raises if `search` "
                    "is missing or ambiguous (more than one match)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Workspace-relative path to the file.",
                        },
                        "search": {
                            "type": "string",
                            "description": "Exact text to replace. Must be unique in the file.",
                        },
                        "replace": {
                            "type": "string",
                            "description": "Replacement text.",
                        },
                    },
                    "required": ["path", "search", "replace"],
                },
            },
        }

    def execute(self, args: dict) -> dict:
        relative = args["path"]
        path = self._root / relative
        search = args["search"]
        replace = args["replace"]
        if not path.exists():
            raise ValueError(f"patch: file not found: {relative}")
        text = path.read_text(encoding="utf-8")
        count = text.count(search)
        if count == 0:
            raise ValueError(f"patch: search not found in {relative}")
        if count > 1:
            raise ValueError(
                f"patch: search is ambiguous in {relative} ({count} matches)"
            )
        path.write_text(text.replace(search, replace, 1), encoding="utf-8")
        print(
            f"[tools.patch] path={relative} replaced={len(search)}->{len(replace)}",
            flush=True,
        )
        return {"ok": True, "path": relative}
