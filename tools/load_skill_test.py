from __future__ import annotations

import pytest

from models import Skill
from tools.load_skill import LoadSkillTool


def _skill(name: str, content: str = "") -> Skill:
    return Skill(name=name, description="", content=content)


def test_schema_shape():
    schema = LoadSkillTool(skills=[]).get_openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "load_skill"
    assert "name" in schema["function"]["parameters"]["properties"]
    assert schema["function"]["parameters"]["required"] == ["name"]


def test_returns_skill_content():
    tool = LoadSkillTool(skills=[_skill("python-developer", "BODY")])
    result = tool.execute({"name": "python-developer"})
    assert result == {"content": "BODY"}


def test_unknown_skill_raises():
    tool = LoadSkillTool(skills=[_skill("a")])
    with pytest.raises(ValueError, match="unknown skill"):
        tool.execute({"name": "missing"})


def test_non_string_name_raises():
    tool = LoadSkillTool(skills=[_skill("a")])
    with pytest.raises(ValueError, match="must be a string"):
        tool.execute({"name": 123})


def test_empty_skills_any_lookup_raises():
    tool = LoadSkillTool(skills=[])
    with pytest.raises(ValueError, match="unknown skill"):
        tool.execute({"name": "anything"})


def test_picks_correct_skill_from_many():
    tool = LoadSkillTool(skills=[_skill("a", "A"), _skill("b", "B"), _skill("c", "C")])
    assert tool.execute({"name": "b"}) == {"content": "B"}
