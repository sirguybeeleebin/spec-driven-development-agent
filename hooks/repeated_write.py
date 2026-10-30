from __future__ import annotations

import json
from typing import Any

from models import AgentRole, Message, State, ToolCall


class RepeatedWritePreHook:
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

        session = state.get(role) or {}
        history: list[Message] = session.get("history") or []

        written = False
        blocked = False
        pending: dict[str, ToolCall] = {}
        for msg in history:
            if msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    pending[tc.id] = tc
            elif msg.role == "tool":
                tc = pending.pop(msg.tool_call_id, None)
                if tc is None or tc.name not in ("append", "patch"):
                    continue
                if tc.arguments.get("path") != path:
                    continue
                try:
                    parsed = json.loads(msg.content)
                except (json.JSONDecodeError, TypeError):
                    parsed = {"raw": msg.content}
                if "hint" in parsed:
                    blocked = True
                elif "error" not in parsed:
                    written = True

        if written and blocked:
            return (
                f"STOP. `{tool_call.name}` on {path!r} already "
                f"succeeded and you have already been told not to "
                f"write it again. Produce the final message "
                f"immediately. Do not call any tool."
            )
        if written:
            return (
                f"`{tool_call.name}` on {path!r} already succeeded; "
                f"the file is written. Do not write to this path "
                f"again."
            )
        return None