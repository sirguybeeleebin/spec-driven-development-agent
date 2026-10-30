from __future__ import annotations

from typing import Any

from models import AgentRole, State, ToolCall


class StopError(Exception):
    """Raised by a post-hook to end the agent session with a final
    summary reply.
    """


class StopAfterWritePostHook:
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
        if path in (state["target"], state["target_test"]):
            raise StopError()