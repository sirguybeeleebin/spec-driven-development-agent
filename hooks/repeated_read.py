from __future__ import annotations

import json
from typing import Any

from models import AgentRole, Message, State, ToolCall


class RepeatedReadPreHook:
    def __call__(
        self,
        *,
        state: State,
        role: AgentRole,
        tool_call: ToolCall,
        args: dict[str, Any],
    ) -> str | None:
        if tool_call.name != "read":
            return None
        path = args.get("path")
        if not isinstance(path, str):
            return None

        session = state.get(role) or {}
        history: list[Message] = session.get("history") or []

        failed = False
        blocked = False
        already_read = False
        pending: dict[str, ToolCall] = {}
        for msg in history:
            if msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    pending[tc.id] = tc
            elif msg.role == "tool":
                tc = pending.pop(msg.tool_call_id, None)
                if tc is None or tc.name != "read":
                    continue
                if tc.arguments.get("path") != path:
                    continue
                try:
                    parsed = json.loads(msg.content)
                except (json.JSONDecodeError, TypeError):
                    parsed = {"raw": msg.content}
                if "hint" in parsed:
                    blocked = True
                elif "error" in parsed:
                    failed = True
                else:
                    already_read = True

        if failed and blocked:
            return (
                f"STOP. `read` on {path!r} has already failed and you "
                f"have already been told not to call it again. This "
                f"path does not exist. Produce the final message "
                f"immediately. Do not call any tool."
            )
        if failed:
            return (
                f"`read` on {path!r} failed: the path does not exist. "
                f"Do not call `read` on this path again. If you have "
                f"no other paths to read, produce the final message "
                f"now."
            )
        if already_read:
            return (
                f"`read` on {path!r} already succeeded; the result is "
                f"in `# History`. Do not call `read` on this path "
                f"again."
            )
        return None