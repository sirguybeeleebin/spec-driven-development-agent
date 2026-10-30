# parsers/skill_test.py

from __future__ import annotations

import pytest

from parsers import parse_skill

_VALID = """\
---
name: python-developer
description: Python development rules.
---

# Body

Rules here.
"""


def parse_skill_parses_valid_skill_test() -> None:
    print(f"[{__name__}] parse_skill_parses_valid_skill_test")
    skill = parse_skill(_VALID)

    assert skill.name == "python-developer"
    assert skill.description == "Python development rules."
    assert skill.content == _VALID


def parse_skill_preserves_raw_content_test() -> None:
    print(f"[{__name__}] parse_skill_preserves_raw_content_test")
    skill = parse_skill(_VALID)

    assert skill.content.startswith("---")
    assert "# Body" in skill.content


def parse_skill_missing_frontmatter_raises_test() -> None:
    print(f"[{__name__}] parse_skill_missing_frontmatter_raises_test")
    with pytest.raises(ValueError, match="missing YAML frontmatter"):
        parse_skill("# No frontmatter\n\nbody\n")


def parse_skill_missing_name_raises_test() -> None:
    print(f"[{__name__}] parse_skill_missing_name_raises_test")
    body = "---\ndescription: only description\n---\n\nbody\n"
    with pytest.raises(ValueError, match="missing 'name'"):
        parse_skill(body)


def parse_skill_missing_description_raises_test() -> None:
    print(f"[{__name__}] parse_skill_missing_description_raises_test")
    body = "---\nname: only-name\n---\n\nbody\n"
    with pytest.raises(ValueError, match="missing 'description'"):
        parse_skill(body)


def parse_skill_empty_name_raises_test() -> None:
    print(f"[{__name__}] parse_skill_empty_name_raises_test")
    body = "---\nname: ''\ndescription: rules\n---\n\nbody\n"
    with pytest.raises(ValueError, match="empty name"):
        parse_skill(body)


def parse_skill_empty_description_raises_test() -> None:
    print(f"[{__name__}] parse_skill_empty_description_raises_test")
    body = "---\nname: python-developer\ndescription: ''\n---\n\nbody\n"
    with pytest.raises(ValueError, match="empty description"):
        parse_skill(body)


def parse_skill_extra_frontmatter_keys_allowed_test() -> None:
    print(f"[{__name__}] parse_skill_extra_frontmatter_keys_allowed_test")
    body = (
        "---\n"
        "name: python-developer\n"
        "description: rules\n"
        "license: MIT\n"
        "compatibility: python>=3.12\n"
        "---\n\n"
        "body\n"
    )
    skill = parse_skill(body)

    assert skill.name == "python-developer"
    assert skill.description == "rules"
