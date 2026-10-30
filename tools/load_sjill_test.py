# tools/load_skill_test.py

from __future__ import annotations

import pytest

from models import Skill
from tools.load_skill import LoadSkillTool


def _skill(name: str, description: str = "desc", content: str = "body") -> Skill:
    return Skill(name=name, description=description, content=content)


@pytest.fixture
def tool() -> LoadSkillTool:
    return LoadSkillTool(
        skills=[
            _skill("alpha", "Alpha skill", "alpha content"),
            _skill("beta", "Beta skill", "beta content"),
        ]
    )


# ---- schema ----


def test_get_openai_schema_shape(tool: LoadSkillTool) -> None:
    schema = tool.get_openai_schema()

    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == "load_skill"
    assert isinstance(fn["description"], str) and fn["description"]

    params = fn["parameters"]
    assert params["type"] == "object"
    assert set(params["properties"]) == {"name"}
    assert params["required"] == ["name"]


# ---- happy path ----


def test_execute_returns_content_of_known_skill(tool: LoadSkillTool) -> None:
    result = tool.execute({"name": "alpha"})
    assert result == {"ok": True, "name": "alpha", "content": "alpha content"}


def test_execute_returns_content_of_other_skill(tool: LoadSkillTool) -> None:
    result = tool.execute({"name": "beta"})
    assert result == {"ok": True, "name": "beta", "content": "beta content"}


def test_execute_single_skill_catalog() -> None:
    single = LoadSkillTool(skills=[_skill("only", content="one")])
    assert single.execute({"name": "only"}) == {
        "ok": True,
        "name": "only",
        "content": "one",
    }


# ---- unknown skill ----


def test_execute_unknown_skill_returns_error(tool: LoadSkillTool) -> None:
    result = tool.execute({"name": "gamma"})
    assert result["ok"] is False
    assert "unknown skill 'gamma'" in result["error"]


def test_execute_unknown_skill_lists_available(tool: LoadSkillTool) -> None:
    result = tool.execute({"name": "gamma"})
    assert result["available"] == ["alpha", "beta"]


def test_execute_empty_catalog_lists_empty_available() -> None:
    empty = LoadSkillTool(skills=[])
    result = empty.execute({"name": "anything"})
    assert result["ok"] is False
    assert "unknown skill" in result["error"]
    assert result["available"] == []


# ---- argument validation ----


def test_execute_missing_name(tool: LoadSkillTool) -> None:
    result = tool.execute({})
    assert result["ok"] is False
    assert "'name' must be a non-empty string" in result["error"]


def test_execute_empty_name(tool: LoadSkillTool) -> None:
    result = tool.execute({"name": ""})
    assert result["ok"] is False
    assert "'name' must be a non-empty string" in result["error"]


def test_execute_non_string_name(tool: LoadSkillTool) -> None:
    result = tool.execute({"name": 42})
    assert result["ok"] is False
    assert "'name' must be a non-empty string" in result["error"]


def test_execute_none_name(tool: LoadSkillTool) -> None:
    result = tool.execute({"name": None})
    assert result["ok"] is False
    assert "'name' must be a non-empty string" in result["error"]


def test_invalid_name_includes_available(tool: LoadSkillTool) -> None:
    result = tool.execute({"name": ""})
    assert result["available"] == ["alpha", "beta"]
