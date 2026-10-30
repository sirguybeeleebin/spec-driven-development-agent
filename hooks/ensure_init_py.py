from __future__ import annotations

from pathlib import Path
from typing import Any

from models import AgentRole, State, ToolCall


class EnsureInitPyPostHook:
    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()

    def __call__(
        self,
        *,
        state: State,
        role: AgentRole,
        tool_call: ToolCall,
        args: dict[str, Any],
        result: dict,
    ) -> None:
        if tool_call.name not in ("append", "patch"):
            return
        if "error" in result:
            return
        path = args.get("path")
        if not isinstance(path, str):
            return
        if not path.endswith(".py"):
            return

        file_path = (self._root / path).resolve()
        current = file_path.parent
        while current != self._root and current.is_relative_to(self._root):
            init = current / "__init__.py"
            if not init.exists():
                try:
                    init.parent.mkdir(parents=True, exist_ok=True)
                    init.write_text("", encoding="utf-8")
                    print(
                        f"[hooks.ensure_init_py] created {init}",
                        flush=True,
                    )
                except OSError as exc:
                    print(
                        f"[hooks.ensure_init_py] failed {init}: "
                        f"{type(exc).__name__}: {exc}",
                        flush=True,
                    )
                    return
            current = current.parent