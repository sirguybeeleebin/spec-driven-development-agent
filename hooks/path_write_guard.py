from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from models import AgentRole, State, ToolCall


class PathWriteGuardPreHook:
    def __call__(
        self,
        *,
        state: State,
        role: AgentRole,
        tool_call: ToolCall,
        args: dict[str, Any],
    ) -> str | None:
        if tool_call.name not in ("append", "patch"):
            return None
        path = args.get("path")
        if not isinstance(path, str):
            return None
        allowed = {state["target"], state["target_test"]}
        if str(PurePosixPath(path)) in allowed:
            return None
        allowed_str = ", ".join(sorted(allowed))
        return (
            f"{tool_call.name} with path={path!r} is not allowed. "
            f"Only these paths may be written for this task: "
            f"{allowed_str}. Do not call `{tool_call.name}` with the "
            f"same `path` again."
        )