# hooks/code_validation.py

from __future__ import annotations

import ast
from pathlib import Path

from models import State, ToolCall
from runners.agent import Hook


class PythonValidationHook(Hook):
    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()

    def after_tool_call(
        self,
        *,
        state: State,
        tool_call: ToolCall,
        result: dict,
    ) -> dict:
        if tool_call.name not in ("append", "patch"):
            return result
        if not result.get("ok"):
            return result

        path_value = tool_call.arguments.get("path")
        if not isinstance(path_value, str) or not path_value.endswith(".py"):
            return result

        candidate = (self._root / path_value).resolve()
        if not candidate.is_relative_to(self._root):
            return result
        if not candidate.is_file():
            return result

        source = candidate.read_text(encoding="utf-8")
        try:
            ast.parse(source)
        except SyntaxError as exc:
            return {
                "ok": False,
                "path": path_value,
                "error": f"{path_value}:{exc.lineno}: {exc.msg}",
            }

        return result
