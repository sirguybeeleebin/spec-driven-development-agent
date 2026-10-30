from __future__ import annotations

import json
from typing import Any

from models import AgentRole, Message, Skill, State, ToolCall


class SkillRequiredPreHook:
    def __init__(self, *, skills: list[Skill]) -> None:
        self._needed = bool(skills)

    def __call__(
        self,
        *,
        state: State,
        role: AgentRole,
        tool_call: ToolCall,
        args: dict[str, Any],
    ) -> str | None:
        if not self._needed:
            return None
        if tool_call.name not in ("read", "append", "patch"):
            return None

        session = state.get(role) or {}
        history: list[Message] = session.get("history") or []

        loaded = False
        pending: dict[str, ToolCall] = {}
        for msg in history:
            if msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    pending[tc.id] = tc
            elif msg.role == "tool":
                tc = pending.pop(msg.tool_call_id, None)
                if tc is None or tc.name != "load_skill":
                    continue
                try:
                    parsed = json.loads(msg.content)
                except (json.JSONDecodeError, TypeError):
                    continue
                if "error" not in parsed:
                    loaded = True
                    break

        if loaded:
            return None
        return (
            f"{tool_call.name} is blocked: no skill has been loaded "
            f"yet. Before any `read`, `append`, or `patch`, call "
            f"`load_skill(name)` for every skill in `# Skills` whose "
            f"description matches the task. Call `load_skill` now."
        )