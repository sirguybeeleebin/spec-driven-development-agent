# app/factory_test.py

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.factory import build_agent
from models import Agents, Skill

# ---- helpers ----


def _any_role() -> Agents:
    return next(iter(Agents))


def _provider_config(**overrides: Any) -> dict[str, Any]:
    base = {
        "temperature": 0.7,
        "base_url": "https://example.invalid/v1",
        "api_key": "k",
        "model": "gpt-x",
    }
    base.update(overrides)
    return base


def _agent_config(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "provider": _provider_config(),
        "skills": [],
        "tools": [],
    }
    base.update(overrides)
    return base


def _config_for(role: Agents, **agent_overrides: Any) -> dict[str, Any]:
    return {"agents": {role.value: _agent_config(**agent_overrides)}}


def _skills() -> dict[str, Skill]:
    return {
        "alpha": Skill(name="alpha", description="a", content="body"),
        "beta": Skill(name="beta", description="b", content="body"),
    }


# ---- dependency mocking ----


@pytest.fixture
def deps(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    sentinels: dict[str, Any] = {}

    def make_openai(**kw):
        captured["openai"] = kw
        s = object()
        sentinels["openai"] = s
        return s

    def make_llm(**kw):
        captured["llm"] = kw
        s = object()
        sentinels["llm"] = s
        return s

    def make_runner(**kw):
        captured["runner"] = kw
        s = object()
        sentinels["runner"] = s
        return s

    def make_tool_factory(name: str):
        def factory(**kw):
            captured.setdefault("tools", []).append((name, kw))
            s = object()
            sentinels[name] = s
            return s

        return factory

    monkeypatch.setattr("app.factory.OpenAI", make_openai)
    monkeypatch.setattr("app.factory.LLMClient", make_llm)
    monkeypatch.setattr("app.factory.AgentRunner", make_runner)
    for tool_name in (
        "AppendTool",
        "PatchTool",
        "ReadTool",
        "BashTool",
        "LoadSkillTool",
    ):
        monkeypatch.setattr(f"app.factory.{tool_name}", make_tool_factory(tool_name))

    return {"captured": captured, "sentinels": sentinels}


def _run(
    deps: dict[str, Any],
    *,
    role: Agents | None = None,
    config: dict[str, Any] | None = None,
    skills: dict[str, Skill] | None = None,
    root: Path | None = None,
    providers: dict[Agents, Any] | None = None,
    hooks: list[Any] | None = None,
) -> Any:
    role = role or _any_role()
    return build_agent(
        role=role,
        config=config if config is not None else _config_for(role),
        skills=skills if skills is not None else {},
        root=root if root is not None else Path("/work"),
        providers=providers if providers is not None else {role: "P"},
        hooks=hooks if hooks is not None else [],
    )


# ---- return value / wiring ----


def test_returns_runner_from_agent_runner(deps: dict[str, Any]) -> None:
    out = _run(deps)
    assert out is deps["sentinels"]["runner"]


def test_runner_receives_llm_instance(deps: dict[str, Any]) -> None:
    _run(deps)
    assert deps["captured"]["runner"]["llm"] is deps["sentinels"]["llm"]


def test_openai_client_built_from_provider_config(
    deps: dict[str, Any],
) -> None:
    role = _any_role()
    cfg = _config_for(
        role,
        provider=_provider_config(base_url="https://x/v1", api_key="secret", model="m"),
    )
    _run(deps, role=role, config=cfg)
    assert deps["captured"]["openai"] == {
        "base_url": "https://x/v1",
        "api_key": "secret",
    }
    assert deps["captured"]["llm"]["model"] == "m"


# ---- opts: temperature / max_tokens ----


def test_temperature_parsed_as_float_from_string(
    deps: dict[str, Any],
) -> None:
    role = _any_role()
    cfg = _config_for(role, provider=_provider_config(temperature="0.5"))
    _run(deps, role=role, config=cfg)
    assert deps["captured"]["llm"]["opts"]["temperature"] == 0.5
    assert isinstance(deps["captured"]["llm"]["opts"]["temperature"], float)


def test_temperature_parsed_as_float_from_int(
    deps: dict[str, Any],
) -> None:
    role = _any_role()
    cfg = _config_for(role, provider=_provider_config(temperature=1))
    _run(deps, role=role, config=cfg)
    t = deps["captured"]["llm"]["opts"]["temperature"]
    assert t == 1.0
    assert isinstance(t, float)


def test_max_tokens_absent_not_in_opts(deps: dict[str, Any]) -> None:
    _run(deps)
    assert "max_tokens" not in deps["captured"]["llm"]["opts"]


def test_max_tokens_present_included_and_cast(
    deps: dict[str, Any],
) -> None:
    role = _any_role()
    cfg = _config_for(role, provider=_provider_config(max_tokens="512"))
    _run(deps, role=role, config=cfg)
    mt = deps["captured"]["llm"]["opts"]["max_tokens"]
    assert mt == 512
    assert isinstance(mt, int)


# ---- skills ----


def test_skills_resolved_from_names_in_order(deps: dict[str, Any]) -> None:
    role = _any_role()
    pool = _skills()
    cfg = _config_for(role, skills=["beta", "alpha"])
    _run(deps, role=role, config=cfg, skills=pool)
    assert deps["captured"]["runner"]["skills"] == [pool["beta"], pool["alpha"]]


def test_missing_skill_raises(deps: dict[str, Any]) -> None:
    role = _any_role()
    cfg = _config_for(role, skills=["ghost"])
    with pytest.raises(ValueError, match="skills not found"):
        _run(deps, role=role, config=cfg, skills=_skills())


def test_missing_skill_lists_all_missing_names(
    deps: dict[str, Any],
) -> None:
    role = _any_role()
    cfg = _config_for(role, skills=["ghost", "phantom"])
    with pytest.raises(ValueError) as exc:
        _run(deps, role=role, config=cfg, skills=_skills())
    msg = str(exc.value)
    assert "ghost" in msg
    assert "phantom" in msg


# ---- tools ----


def test_empty_tools_produces_empty_list(deps: dict[str, Any]) -> None:
    _run(deps)
    assert deps["captured"]["runner"]["tools"] == []
    assert "tools" not in deps["captured"]


def test_tools_built_in_declared_order(deps: dict[str, Any]) -> None:
    role = _any_role()
    cfg = _config_for(role, tools=["bash", "read", "patch", "append"])
    _run(deps, role=role, config=cfg)
    built = [name for name, _ in deps["captured"]["tools"]]
    assert built == ["BashTool", "ReadTool", "PatchTool", "AppendTool"]


def test_root_propagated_to_file_tools(deps: dict[str, Any]) -> None:
    role = _any_role()
    cfg = _config_for(role, tools=["append", "patch", "read", "bash"])
    root = Path("/some/root")
    _run(deps, role=role, config=cfg, root=root)
    for _, kwargs in deps["captured"]["tools"]:
        assert kwargs == {"root": root}


def test_load_skill_gets_role_skills(deps: dict[str, Any]) -> None:
    role = _any_role()
    pool = _skills()
    cfg = _config_for(role, skills=["alpha", "beta"], tools=["load_skill"])
    _run(deps, role=role, config=cfg, skills=pool)
    assert deps["captured"]["tools"] == [
        ("LoadSkillTool", {"skills": [pool["alpha"], pool["beta"]]})
    ]


def test_load_skill_without_skills_raises(deps: dict[str, Any]) -> None:
    role = _any_role()
    cfg = _config_for(role, skills=[], tools=["load_skill"])
    with pytest.raises(ValueError, match="has no skills"):
        _run(deps, role=role, config=cfg)


def test_unknown_tool_raises(deps: dict[str, Any]) -> None:
    role = _any_role()
    cfg = _config_for(role, tools=["wat"])
    with pytest.raises(ValueError, match="unknown tool"):
        _run(deps, role=role, config=cfg)


def test_unknown_tool_error_includes_name(deps: dict[str, Any]) -> None:
    role = _any_role()
    cfg = _config_for(role, tools=["wat"])
    with pytest.raises(ValueError) as exc:
        _run(deps, role=role, config=cfg)
    assert "wat" in str(exc.value)


# ---- max_iterations ----


def test_max_iterations_defaults_to_15(deps: dict[str, Any]) -> None:
    _run(deps)
    assert deps["captured"]["runner"]["max_iterations"] == 15


def test_max_iterations_from_config(deps: dict[str, Any]) -> None:
    role = _any_role()
    cfg = _config_for(role, max_iterations=5)
    _run(deps, role=role, config=cfg)
    assert deps["captured"]["runner"]["max_iterations"] == 5


def test_max_iterations_string_parsed(deps: dict[str, Any]) -> None:
    role = _any_role()
    cfg = _config_for(role, max_iterations="7")
    _run(deps, role=role, config=cfg)
    assert deps["captured"]["runner"]["max_iterations"] == 7


# ---- provider / hooks passthrough ----


def test_provider_from_dict_passed_through(deps: dict[str, Any]) -> None:
    role = _any_role()
    provider = object()
    _run(deps, role=role, providers={role: provider})
    assert deps["captured"]["runner"]["prompt_provider"] is provider


def test_hooks_passed_through_verbatim(deps: dict[str, Any]) -> None:
    h1, h2 = object(), object()
    _run(deps, hooks=[h1, h2])
    assert deps["captured"]["runner"]["hooks"] == [h1, h2]
