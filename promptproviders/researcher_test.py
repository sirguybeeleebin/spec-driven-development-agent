# promptproviders/researcher_test.py

from __future__ import annotations

import pytest

from models import Skill, State
from models.task import Declaration, Interface
from promptproviders.researcher import ResearcherPromptProvider

# If Declaration/Interface carry additional required fields, or are
# re-exported via models/__init__.py, adjust the imports/constructors
# below — the test bodies only exercise ``name`` on declarations and
# ``name`` / ``language`` / ``description`` / ``steps`` / ``content``
# on interfaces, which is exactly what the provider reads.

SYSTEM = "You are a researcher."
USER_TEMPLATE = (
    "Goal: {goal}\n"
    "Target: {target_file}\n"
    "Declares:\n{declares}\n"
    "Interfaces:\n{interfaces}"
)
FINAL = "Final summary please."


# ---- helpers ----


def _skill(
    name: str,
    description: str = "desc",
    content: str = "",
) -> Skill:
    return Skill(name=name, description=description, content=content)


def _declaration(name: str) -> Declaration:
    return Declaration(name=name)


def _interface(
    name: str,
    *,
    language: str = "python",
    description: str = "",
    steps: list[str] | None = None,
    content: str = "",
) -> Interface:
    return Interface(
        name=name,
        language=language,
        description=description,
        steps=steps or [],
        content=content,
    )


@pytest.fixture
def provider() -> ResearcherPromptProvider:
    return ResearcherPromptProvider(
        system_template=SYSTEM,
        user_template=USER_TEMPLATE,
        final_prompt=FINAL,
    )


# ---- format_system ----


def test_format_system_no_skills_returns_template(
    provider: ResearcherPromptProvider,
) -> None:
    assert provider.format_system([]) == SYSTEM


def test_format_system_with_one_skill(
    provider: ResearcherPromptProvider,
) -> None:
    out = provider.format_system([_skill("alpha", "does alpha")])
    assert out == f"{SYSTEM}\n\n# Skills\n\n- `alpha`: does alpha"


def test_format_system_with_multiple_skills_in_order(
    provider: ResearcherPromptProvider,
) -> None:
    out = provider.format_system([_skill("a", "aa"), _skill("b", "bb")])
    assert out == f"{SYSTEM}\n\n# Skills\n\n- `a`: aa\n- `b`: bb"


def test_format_system_preserves_custom_system() -> None:
    custom = ResearcherPromptProvider(
        system_template="MY SYS",
        user_template="{goal}{target_file}{declares}{interfaces}",
        final_prompt="F",
    )
    out = custom.format_system([_skill("a", "b")])
    assert out == "MY SYS\n\n# Skills\n\n- `a`: b"


# ---- final_user ----


def test_final_user_returns_configured_string(
    provider: ResearcherPromptProvider,
) -> None:
    assert provider.final_user == FINAL


def test_final_user_empty_when_configured_empty() -> None:
    p = ResearcherPromptProvider(
        system_template="",
        user_template="{goal}{target_file}{declares}{interfaces}",
        final_prompt="",
    )
    assert p.final_user == ""


# ---- format_user: scalar fields ----


def test_format_user_empty_state_uses_none_placeholders(
    provider: ResearcherPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Goal: _(none)_" in out
    assert "Declares:\n_(none)_" in out
    assert "Interfaces:\n_(none)_" in out


def test_format_user_goal_and_target_file(
    provider: ResearcherPromptProvider,
) -> None:
    out = provider.format_user(State(goal="build x", target_file="src/x.py"))
    assert "Goal: build x" in out
    assert "Target: src/x.py" in out


def test_format_user_empty_goal_rendered_as_none(
    provider: ResearcherPromptProvider,
) -> None:
    out = provider.format_user(State(target_file="x.py"))
    assert "Goal: _(none)_" in out


def test_format_user_empty_target_file_stays_empty(
    provider: ResearcherPromptProvider,
) -> None:
    # target_file has no _(none)_ fallback — only goal/declares/interfaces do.
    out = provider.format_user(State(goal="g"))
    assert "Target: \n" in out
    assert "Target: _(none)_" not in out


# ---- format_user: declares ----


def test_format_user_declares_rendered_as_bullets(
    provider: ResearcherPromptProvider,
) -> None:
    state = State(declares=[_declaration("Foo"), _declaration("Bar")])
    out = provider.format_user(state)
    assert "- `Foo`\n- `Bar`" in out


def test_format_user_empty_declares_rendered_as_none(
    provider: ResearcherPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Declares:\n_(none)_" in out


# ---- format_user: interfaces ----


def test_format_user_interface_minimal_block(
    provider: ResearcherPromptProvider,
) -> None:
    # No description and no steps → those sections must be omitted entirely.
    iface = _interface("Repo", language="python", content="class Repo: pass")
    out = provider.format_user(State(interfaces=[iface]))
    assert "## Interface: Repo" in out
    assert "Language: python" in out
    assert "Description:" not in out
    assert "Steps:" not in out
    assert "```python\nclass Repo: pass\n```" in out


def test_format_user_interface_with_description(
    provider: ResearcherPromptProvider,
) -> None:
    iface = _interface("Repo", description="a repository pattern", content="pass")
    out = provider.format_user(State(interfaces=[iface]))
    assert "Description: a repository pattern" in out


def test_format_user_interface_with_steps(
    provider: ResearcherPromptProvider,
) -> None:
    iface = _interface("Repo", steps=["open", "read", "close"], content="pass")
    out = provider.format_user(State(interfaces=[iface]))
    assert "Steps:\n1. open\n2. read\n3. close" in out


def test_format_user_interface_full_block(
    provider: ResearcherPromptProvider,
) -> None:
    # Locks in the exact section layout: sections separated by blank lines.
    iface = _interface(
        "Repo",
        language="python",
        description="repo",
        steps=["open", "read"],
        content="class Repo: pass",
    )
    out = provider.format_user(State(interfaces=[iface]))
    expected = (
        "## Interface: Repo\n\n"
        "Language: python\n\n"
        "Description: repo\n\n"
        "Steps:\n1. open\n2. read\n\n"
        "```python\nclass Repo: pass\n```"
    )
    assert expected in out


def test_format_user_multiple_interfaces_separated_by_blank_line(
    provider: ResearcherPromptProvider,
) -> None:
    a = _interface("A", content="a")
    b = _interface("B", content="b")
    out = provider.format_user(State(interfaces=[a, b]))
    assert "```python\na\n```\n\n## Interface: B" in out


def test_format_user_empty_interfaces_rendered_as_none(
    provider: ResearcherPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Interfaces:\n_(none)_" in out


def test_format_user_interface_empty_language(
    provider: ResearcherPromptProvider,
) -> None:
    iface = _interface("X", language="", content="hi")
    out = provider.format_user(State(interfaces=[iface]))
    assert "## Interface: X\n\nLanguage: \n\n```\nhi\n```" in out


# ---- format_user: template mechanics ----


def test_format_user_uses_configured_user_template() -> None:
    p = ResearcherPromptProvider(
        system_template="SYS",
        user_template="G={goal} F={target_file} D={declares} I={interfaces}",
        final_prompt="F",
    )
    out = p.format_user(State(goal="go", target_file="x.py"))
    assert out == "G=go F=x.py D=_(none)_ I=_(none)_"


def test_format_user_values_with_braces_are_literal(
    provider: ResearcherPromptProvider,
) -> None:
    # Values containing `{}` must not be reinterpreted by str.format.
    iface = _interface("Repo", content="def f(x: dict = {}): ...")
    state = State(goal="use {braces}", interfaces=[iface])
    out = provider.format_user(state)
    assert "use {braces}" in out
    assert "def f(x: dict = {}): ..." in out


def test_format_user_does_not_reformat_substituted_values(
    provider: ResearcherPromptProvider,
) -> None:
    # A value that itself looks like a format token must be preserved verbatim.
    out = provider.format_user(State(goal="{target_file}"))
    assert "Goal: {target_file}" in out
