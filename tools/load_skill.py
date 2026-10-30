# tools/load_skill.py

from __future__ import annotations

from models import Skill


class LoadSkillTool:
    def __init__(self, *, skills: list[Skill]) -> None:
        self._by_name = {s.name: s for s in skills}

    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": (
                    "Load the full content of a skill by name. The "
                    "catalog of skill names is in the system prompt "
                    "under `# Skills`."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Skill name.",
                        },
                    },
                    "required": ["name"],
                },
            },
        }

    def execute(self, args: dict) -> dict:
        name = args.get("name")
        if not isinstance(name, str) or not name:
            return {
                "ok": False,
                "error": "load_skill: 'name' must be a non-empty string",
                "available": sorted(self._by_name),
            }

        skill = self._by_name.get(name)
        if skill is None:
            return {
                "ok": False,
                "error": (
                    f"load_skill: unknown skill {name!r}. "
                    f"Known: {sorted(self._by_name)}"
                ),
                "available": sorted(self._by_name),
            }

        return {"ok": True, "name": name, "content": skill.content}
