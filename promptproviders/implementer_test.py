# promptproviders/implementer_test.py

from __future__ import annotations

import pytest

from models import Skill, State
from models.task import Declaration, Interface, Sequence
from promptproviders.implementer import ImplementerPromptProvider

# If Declaration/Interface/Sequence carry additional required fields, or
# are re-exported via models/__init__.py, adjust the imports/constructors
# below — the provider only reads ``name`` on declarations, ``name`` /
# ``language`` / ``description`` / ``steps`` / ``content`` on interfaces,
# and ``language`` / ``content`` on sequences.

SYSTEM = "You are an implementer."
USER_TEMPLATE = (
    "Goal: {goal}\n"
    "Target: {target_file}\n"
    "Declares:\n{declares}\n"
    "Interfaces:\n{interfaces}\n"
    "Researcher:\n{researcher_summary}\n"
    "Constitution:\n{constitution}\n"
    "Sequence:\n{sequence}"
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


def _sequence(language: str = "python", content: str = "s = 1") -> Sequence:
    return Sequence(language=language, content=content)


@pytest.fixture
def provider() -> ImplementerPromptProvider:
    return ImplementerPromptProvider(
        system_template=SYSTEM,
        user_template=USER_TEMPLATE,
        final_prompt=FINAL,
    )


# ---- format_system ----


def test_format_system_no_skills_returns_template(
    provider: ImplementerPromptProvider,
) -> None:
    assert provider.format_system([]) == SYSTEM


def test_format_system_with_one_skill(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_system([_skill("alpha", "does alpha")])
    assert out == f"{SYSTEM}\n\n# Skills\n\n- `alpha`: does alpha"


def test_format_system_with_multiple_skills_in_order(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_system([_skill("a", "aa"), _skill("b", "bb")])
    assert out == f"{SYSTEM}\n\n# Skills\n\n- `a`: aa\n- `b`: bb"


def test_format_system_preserves_custom_system() -> None:
    custom = ImplementerPromptProvider(
        system_template="MY SYS",
        user_template="{goal}{target_file}{declares}{researcher_summary}"
        "{constitution}{interfaces}{sequence}",
        final_prompt="F",
    )
    out = custom.format_system([_skill("a", "b")])
    assert out == "MY SYS\n\n# Skills\n\n- `a`: b"


# ---- final_user ----


def test_final_user_returns_configured_string(
    provider: ImplementerPromptProvider,
) -> None:
    assert provider.final_user == FINAL


def test_final_user_empty_when_configured_empty() -> None:
    p = ImplementerPromptProvider(
        system_template="",
        user_template=(
            "{goal}{target_file}{declares}{researcher_summary}"
            "{constitution}{interfaces}{sequence}"
        ),
        final_prompt="",
    )
    assert p.final_user == ""


# ---- format_user: empty state defaults ----


def test_format_user_empty_state_uses_none_placeholders(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Goal: _(none)_" in out
    assert "Declares:\n_(none)_" in out
    assert "Interfaces:\n_(none)_" in out
    assert "Researcher:\n_(none)_" in out
    assert "Constitution:\n_(none)_" in out
    assert "Sequence:\n_(none)_" in out


# ---- format_user: scalar fields ----


def test_format_user_goal_and_target_file(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_user(State(goal="build x", target_file="src/x.py"))
    assert "Goal: build x" in out
    assert "Target: src/x.py" in out


def test_format_user_empty_goal_rendered_as_none(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_user(State(target_file="x.py"))
    assert "Goal: _(none)_" in out


def test_format_user_empty_target_file_stays_empty(
    provider: ImplementerPromptProvider,
) -> None:
    # target_file has no _(none)_ fallback — only goal/declares/interfaces/
    # researcher_summary/constitution/sequence do.
    out = provider.format_user(State(goal="g"))
    assert "Target: \n" in out
    assert "Target: _(none)_" not in out


# ---- format_user: declares ----


def test_format_user_declares_rendered_as_bullets(
    provider: ImplementerPromptProvider,
) -> None:
    state = State(declares=[_declaration("Foo"), _declaration("Bar")])
    out = provider.format_user(state)
    assert "- `Foo`\n- `Bar`" in out


def test_format_user_empty_declares_rendered_as_none(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Declares:\n_(none)_" in out


# ---- format_user: interfaces ----


def test_format_user_interface_minimal_block(
    provider: ImplementerPromptProvider,
) -> None:
    iface = _interface("Repo", language="python", content="class Repo: pass")
    out = provider.format_user(State(interfaces=[iface]))
    assert "## Interface: Repo" in out
    assert "Language: python" in out
    assert "Description:" not in out
    assert "Steps:" not in out
    assert "```python\nclass Repo: pass\n```" in out


def test_format_user_interface_with_description(
    provider: ImplementerPromptProvider,
) -> None:
    iface = _interface("Repo", description="a repository pattern", content="pass")
    out = provider.format_user(State(interfaces=[iface]))
    assert "Description: a repository pattern" in out


def test_format_user_interface_with_steps(
    provider: ImplementerPromptProvider,
) -> None:
    iface = _interface("Repo", steps=["open", "read", "close"], content="pass")
    out = provider.format_user(State(interfaces=[iface]))
    assert "Steps:\n1. open\n2. read\n3. close" in out


def test_format_user_interface_full_block(
    provider: ImplementerPromptProvider,
) -> None:
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
    provider: ImplementerPromptProvider,
) -> None:
    a = _interface("A", content="a")
    b = _interface("B", content="b")
    out = provider.format_user(State(interfaces=[a, b]))
    assert "```python\na\n```\n\n## Interface: B" in out


def test_format_user_empty_interfaces_rendered_as_none(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Interfaces:\n_(none)_" in out


def test_format_user_interface_empty_language(
    provider: ImplementerPromptProvider,
) -> None:
    iface = _interface("X", language="", content="hi")
    out = provider.format_user(State(interfaces=[iface]))
    assert "## Interface: X\n\nLanguage: \n\n```\nhi\n```" in out


# ---- format_user: researcher_summary ----


def test_format_user_researcher_summary_verbatim(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_user(State(researcher_summary="R output"))
    assert "Researcher:\nR output" in out


def test_format_user_researcher_summary_is_stripped(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_user(State(researcher_summary="  R output\n\n"))
    assert "Researcher:\nR output\n" in out


def test_format_user_empty_researcher_summary_rendered_as_none(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Researcher:\n_(none)_" in out


def test_format_user_whitespace_only_researcher_summary_rendered_as_none(
    provider: ImplementerPromptProvider,
) -> None:
    # Unlike goal, researcher_summary is stripped before the truthiness
    # check, so whitespace-only input collapses to _(none)_.
    out = provider.format_user(State(researcher_summary="   \n\t  "))
    assert "Researcher:\n_(none)_" in out


# ---- format_user: constitution ----


def test_format_user_constitution_verbatim(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_user(State(constitution="Be careful."))
    assert "Constitution:\nBe careful." in out


def test_format_user_empty_constitution_rendered_as_none(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Constitution:\n_(none)_" in out


def test_format_user_constitution_not_stripped(
    provider: ImplementerPromptProvider,
) -> None:
    # constitution uses plain ``or`` (no strip) — whitespace survives.
    out = provider.format_user(State(constitution="  spaced  "))
    assert "Constitution:\n  spaced  \n" in out


# ---- format_user: sequence ----


def test_format_user_sequence_fenced_block(
    provider: ImplementerPromptProvider,
) -> None:
    seq = _sequence(language="python", content="a = 1\nb = 2")
    out = provider.format_user(State(sequence=seq))
    assert "Sequence:\n```python\na = 1\nb = 2\n```" in out


def test_format_user_sequence_none_rendered_as_none(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_user(State(sequence=None))
    assert "Sequence:\n_(none)_" in out


def test_format_user_sequence_empty_language(
    provider: ImplementerPromptProvider,
) -> None:
    seq = _sequence(language="", content="body")
    out = provider.format_user(State(sequence=seq))
    assert "Sequence:\n```\nbody\n```" in out


def test_format_user_sequence_empty_content(
    provider: ImplementerPromptProvider,
) -> None:
    seq = _sequence(language="python", content="")
    out = provider.format_user(State(sequence=seq))
    assert "Sequence:\n```python\n\n```" in out


# ---- format_user: template mechanics ----


def test_format_user_uses_configured_user_template() -> None:
    p = ImplementerPromptProvider(
        system_template="SYS",
        user_template=(
            "G={goal} F={target_file} D={declares} I={interfaces} "
            "R={researcher_summary} C={constitution} S={sequence}"
        ),
        final_prompt="F",
    )
    out = p.format_user(State(goal="go", target_file="x.py"))
    assert out == "G=go F=x.py D=_(none)_ I=_(none)_ R=_(none)_ C=_(none)_ S=_(none)_"


def test_format_user_values_with_braces_are_literal(
    provider: ImplementerPromptProvider,
) -> None:
    # Values containing ``{}`` must not be reinterpreted by str.format.
    iface = _interface("Repo", content="def f(x: dict = {}): ...")
    seq = _sequence(content="cfg = {}")
    state = State(
        goal="use {braces}",
        interfaces=[iface],
        sequence=seq,
    )
    out = provider.format_user(state)
    assert "use {braces}" in out
    assert "def f(x: dict = {}): ..." in out
    assert "cfg = {}" in out


def test_format_user_does_not_reformat_substituted_values(
    provider: ImplementerPromptProvider,
) -> None:
    out = provider.format_user(State(goal="{target_file}"))
    assert "Goal: {target_file}" in out


# ---- provider isolation ----


def test_two_providers_do_not_share_state() -> None:
    a = ImplementerPromptProvider(
        system_template="A",
        user_template="{goal}|{target_file}|{declares}|{researcher_summary}"
        "|{constitution}|{interfaces}|{sequence}",
        final_prompt="FA",
    )
    b = ImplementerPromptProvider(
        system_template="B",
        user_template="X{goal}",
        final_prompt="FB",
    )
    out_a = a.format_user(State(goal="g"))
    out_b = b.format_user(State(goal="g"))
    assert out_a == "g||_(none)_|_(none)_|_(none)_|_(none)_|_(none)_"
    assert out_b == "Xg"
    assert a.final_user == "FA"
    assert b.final_user == "FB"
