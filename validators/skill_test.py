# validators/skill_test.py

from __future__ import annotations

import pytest

from models import Skill
from validators import validate_skill


def _skill(
    name: str = "python-developer",
    description: str = "rules",
    content: str = "# Body",
) -> Skill:
    return Skill(name=name, description=description, content=content)


def validate_skill_accepts_valid_skill_test() -> None:
    print(f"[{__name__}] validate_skill_accepts_valid_skill_test")
    validate_skill(_skill())


def validate_skill_empty_name_raises_test() -> None:
    print(f"[{__name__}] validate_skill_empty_name_raises_test")
    with pytest.raises(ValueError, match="empty name"):
        validate_skill(_skill(name=""))


def validate_skill_empty_description_raises_test() -> None:
    print(f"[{__name__}] validate_skill_empty_description_raises_test")
    with pytest.raises(ValueError, match="empty description"):
        validate_skill(_skill(description=""))


def validate_skill_empty_content_raises_test() -> None:
    print(f"[{__name__}] validate_skill_empty_content_raises_test")
    with pytest.raises(ValueError, match="empty content"):
        validate_skill(_skill(content=""))
