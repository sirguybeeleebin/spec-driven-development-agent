from __future__ import annotations

import json
from typing import Any

from models import AgentRole, Message, State, ToolCall


class SkillDedupPreHook:
    def __call__(
        self,
        *,
        state: State,
        role: AgentRole,
        tool_call: ToolCall,
        args: dict[str, Any],
    ) -> str | None:
        if tool_call.name != "load_skill":
            return None
        name = args.get("name")
        if not isinstance(name, str):
            return None

        session = state.get(role) or {}
        history: list[Message] = session.get("history") or []

        pending: dict[str, ToolCall] = {}
        for msg in history:
            if msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    pending[tc.id] = tc
            elif msg.role == "tool":
                tc = pending.pop(msg.tool_call_id, None)
                if tc is None or tc.name != "load_skill":
                    continue
                if tc.arguments.get("name") != name:
                    continue
                try:
                    parsed = json.loads(msg.content)
                except (json.JSONDecodeError, TypeError):
                    continue
                if "error" not in parsed and "hint" not in parsed:
                    return (
                        f"Skill '{name}' is already loaded. Its full "
                        f"content is in the tool result above in "
                        f"`# History`. Do not call `load_skill` for "
                        f"this skill again — proceed with the task."
                    )
        return None