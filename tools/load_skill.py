from __future__ import annotations

from typing import Any

from models import Skill


class LoadSkillTool:
    def __init__(self, *, skills: list[Skill]) -> None:
        self._skills: dict[str, Skill] = {s.name: s for s in skills}

    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": (
                    "Return the full body of a skill by name. "
                    "Call this before writing code that depends on a "
                    "skill listed in `# Skills`."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Skill name, exactly as listed in `# Skills`.",
                        }
                    },
                    "required": ["name"],
                },
            },
        }

    def execute(self, args: dict[str, Any]) -> dict:
        name = args.get("name")
        if not isinstance(name, str):
            raise ValueError(f"load_skill: 'name' must be a string, got {name!r}")
        skill = self._skills.get(name)
        if skill is None:
            raise ValueError(f"load_skill: unknown skill: {name}")
        return {"content": skill.content}
