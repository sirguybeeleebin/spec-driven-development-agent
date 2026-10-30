# parsers/skill.py

from __future__ import annotations

import re

import yaml

from models import Skill

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_skill(text: str) -> Skill:
    fm = _FRONTMATTER.match(text)
    if fm is None:
        raise ValueError("skill: missing YAML frontmatter")
    meta = yaml.safe_load(fm.group(1)) or {}
    if "name" not in meta:
        raise ValueError("skill: frontmatter missing 'name'")
    if "description" not in meta:
        raise ValueError("skill: frontmatter missing 'description'")
    name = str(meta["name"])
    description = str(meta["description"])
    if not name:
        raise ValueError("skill: empty name")
    if not description:
        raise ValueError("skill: empty description")
    return Skill(
        name=name,
        description=description,
        content=text,
    )
