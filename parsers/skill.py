# parsers/skill.py

from __future__ import annotations

import re

from models import Skill

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_skill(text: str) -> Skill:
    fm = _FRONTMATTER.match(text)
    if fm is None:
        raise ValueError("skill: missing frontmatter block")

    meta: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []
    for raw_line in fm.group(1).splitlines():
        if not raw_line.strip():
            continue
        if raw_line[0] not in (" ", "\t") and ":" in raw_line:
            if current_key is not None:
                meta[current_key] = " ".join(current_lines).strip()
            key, _, value = raw_line.partition(":")
            current_key = key.strip()
            current_lines = [value.strip()]
        elif current_key is not None:
            current_lines.append(raw_line.strip())
    if current_key is not None:
        meta[current_key] = " ".join(current_lines).strip()

    if "name" not in meta:
        raise ValueError("skill: frontmatter missing 'name'")
    if "description" not in meta:
        raise ValueError("skill: frontmatter missing 'description'")

    name = "".join(c for c in meta["name"] if not c.isspace() and c.isprintable())
    if not name:
        raise ValueError(f"skill: empty name (raw value {meta['name']!r})")
    if not re.fullmatch(r"[a-z0-9-]+", name):
        raise ValueError(
            f"skill: name must match [a-z0-9-]+, got {name!r} "
            f"(raw value {meta['name']!r})"
        )

    description = meta["description"].strip()
    if not description:
        raise ValueError(f"skill {name!r}: empty description")

    content = text[fm.end() :].strip()
    if not content:
        raise ValueError(f"skill {name!r}: empty body after frontmatter")

    return Skill(
        name=name,
        description=description,
        content=content,
    )
