# validators/skill.py

from __future__ import annotations

from models import Skill


def validate_skill(skill: Skill) -> None:
    if not skill.name:
        raise ValueError("skill: empty name")
    if not skill.description:
        raise ValueError("skill: empty description")
    if not skill.content:
        raise ValueError("skill: empty content")
