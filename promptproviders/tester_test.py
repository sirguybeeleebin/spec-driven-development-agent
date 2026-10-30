# promptproviders/tester_test.py

from __future__ import annotations

import pytest

from models import Skill, State
from models.task import Declaration, Gherkin, Interface, Sequence
from promptproviders.tester import TesterPromptProvider

# If Declaration/Interface/Sequence/Gherkin carry additional required
# fields, or are re-exported via models/__init__.py, adjust the imports
# and constructors below — the provider only reads:
#   - ``name`` on declarations
#   - ``name`` / ``language`` / ``description`` / ``steps`` / ``content``
#     on interfaces
#   - ``language`` / ``content`` on sequences
#   - ``name`` / ``given`` / ``when`` / ``then`` on gherkins

SYSTEM = "You are a tester."
USER_TEMPLATE = (
    "TargetTest: {target_test_file}\n"
    "TargetDecl: {target_declaration}\n"
    "TestFn: {test_function}\n"
    "Gherkin:\n{gherkin}\n"
    "Declares:\n{declares}\n"
    "Interfaces:\n{interfaces}\n"
    "Sequence:\n{sequence}\n"
    "Implementer:\n{implementer_summary}"
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


def _gherkin(
    name: str = "scenario",
    *,
    given: list[str] | None = None,
    when: list[str] | None = None,
    then: list[str] | None = None,
) -> Gherkin:
    return Gherkin(
        name=name,
        target_declaration="X",
        given=given if given is not None else ["g"],
        when=when if when is not None else ["w"],
        then=then if then is not None else ["t"],
    )


@pytest.fixture
def provider() -> TesterPromptProvider:
    return TesterPromptProvider(
        system_template=SYSTEM,
        user_template=USER_TEMPLATE,
        final_prompt=FINAL,
    )


# ---- format_system ----


def test_format_system_no_skills_returns_template(
    provider: TesterPromptProvider,
) -> None:
    assert provider.format_system([]) == SYSTEM


def test_format_system_with_one_skill(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_system([_skill("alpha", "does alpha")])
    assert out == f"{SYSTEM}\n\n# Skills\n\n- `alpha`: does alpha"


def test_format_system_with_multiple_skills_in_order(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_system([_skill("a", "aa"), _skill("b", "bb")])
    assert out == f"{SYSTEM}\n\n# Skills\n\n- `a`: aa\n- `b`: bb"


def test_format_system_preserves_custom_system() -> None:
    custom = TesterPromptProvider(
        system_template="MY SYS",
        user_template=(
            "{target_test_file}{target_declaration}{test_function}"
            "{gherkin}{declares}{interfaces}{sequence}"
            "{implementer_summary}"
        ),
        final_prompt="F",
    )
    out = custom.format_system([_skill("a", "b")])
    assert out == "MY SYS\n\n# Skills\n\n- `a`: b"


# ---- final_user ----


def test_final_user_returns_configured_string(
    provider: TesterPromptProvider,
) -> None:
    assert provider.final_user == FINAL


def test_final_user_empty_when_configured_empty() -> None:
    p = TesterPromptProvider(
        system_template="",
        user_template=(
            "{target_test_file}{target_declaration}{test_function}"
            "{gherkin}{declares}{interfaces}{sequence}"
            "{implementer_summary}"
        ),
        final_prompt="",
    )
    assert p.final_user == ""


# ---- format_user: empty state defaults ----


def test_format_user_empty_state_uses_none_placeholders(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "TargetDecl: _(none)_" in out
    assert "Gherkin:\n_(none)_" in out
    assert "Declares:\n_(none)_" in out
    assert "Interfaces:\n_(none)_" in out
    assert "Sequence:\n_(none)_" in out
    assert "Implementer:\n_(none)_" in out


# ---- format_user: scalar fields ----


def test_format_user_target_test_file_verbatim(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_user(State(target_test_file="src/x_test.py"))
    assert "TargetTest: src/x_test.py" in out


def test_format_user_empty_target_test_file_stays_empty(
    provider: TesterPromptProvider,
) -> None:
    # target_test_file has no _(none)_ fallback.
    out = provider.format_user(State(target_test_file=""))
    assert "TargetTest: \n" in out
    assert "TargetTest: _(none)_" not in out


def test_format_user_target_declaration_verbatim(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_user(State(target_declaration="Repo"))
    assert "TargetDecl: Repo" in out


def test_format_user_empty_target_declaration_rendered_as_none(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_user(State(target_declaration=""))
    assert "TargetDecl: _(none)_" in out


def test_format_user_test_function_verbatim(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_user(State(test_function="test_get"))
    assert "TestFn: test_get" in out


def test_format_user_empty_test_function_stays_empty(
    provider: TesterPromptProvider,
) -> None:
    # test_function has no _(none)_ fallback.
    out = provider.format_user(State(test_function=""))
    assert "TestFn: \n" in out
    assert "TestFn: _(none)_" not in out


# ---- format_user: declares ----


def test_format_user_declares_rendered_as_bullets(
    provider: TesterPromptProvider,
) -> None:
    state = State(declares=[_declaration("Foo"), _declaration("Bar")])
    out = provider.format_user(state)
    assert "- `Foo`\n- `Bar`" in out


def test_format_user_empty_declares_rendered_as_none(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Declares:\n_(none)_" in out


# ---- format_user: interfaces ----


def test_format_user_interface_minimal_block(
    provider: TesterPromptProvider,
) -> None:
    iface = _interface("Repo", language="python", content="class Repo: pass")
    out = provider.format_user(State(interfaces=[iface]))
    assert "## Interface: Repo" in out
    assert "Language: python" in out
    assert "Description:" not in out
    assert "Steps:" not in out
    assert "```python\nclass Repo: pass\n```" in out


def test_format_user_interface_with_description(
    provider: TesterPromptProvider,
) -> None:
    iface = _interface("Repo", description="a repository pattern", content="pass")
    out = provider.format_user(State(interfaces=[iface]))
    assert "Description: a repository pattern" in out


def test_format_user_interface_with_steps(
    provider: TesterPromptProvider,
) -> None:
    iface = _interface("Repo", steps=["open", "read", "close"], content="pass")
    out = provider.format_user(State(interfaces=[iface]))
    assert "Steps:\n1. open\n2. read\n3. close" in out


def test_format_user_interface_full_block(
    provider: TesterPromptProvider,
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
    provider: TesterPromptProvider,
) -> None:
    a = _interface("A", content="a")
    b = _interface("B", content="b")
    out = provider.format_user(State(interfaces=[a, b]))
    assert "```python\na\n```\n\n## Interface: B" in out


def test_format_user_empty_interfaces_rendered_as_none(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Interfaces:\n_(none)_" in out


def test_format_user_interface_empty_language(
    provider: TesterPromptProvider,
) -> None:
    iface = _interface("X", language="", content="hi")
    out = provider.format_user(State(interfaces=[iface]))
    assert "## Interface: X\n\nLanguage: \n\n```\nhi\n```" in out


# ---- format_user: sequence ----


def test_format_user_sequence_fenced_block(
    provider: TesterPromptProvider,
) -> None:
    seq = _sequence(language="python", content="a = 1\nb = 2")
    out = provider.format_user(State(sequence=seq))
    assert "Sequence:\n```python\na = 1\nb = 2\n```" in out


def test_format_user_sequence_none_rendered_as_none(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_user(State(sequence=None))
    assert "Sequence:\n_(none)_" in out


def test_format_user_sequence_empty_language(
    provider: TesterPromptProvider,
) -> None:
    seq = _sequence(language="", content="body")
    out = provider.format_user(State(sequence=seq))
    assert "Sequence:\n```\nbody\n```" in out


def test_format_user_sequence_empty_content(
    provider: TesterPromptProvider,
) -> None:
    seq = _sequence(language="python", content="")
    out = provider.format_user(State(sequence=seq))
    assert "Sequence:\n```python\n\n```" in out


# ---- format_user: gherkin ----


def test_format_user_gherkin_none_rendered_as_none(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_user(State(gherkin=None))
    assert "Gherkin:\n_(none)_" in out


def test_format_user_gherkin_full_scenario(
    provider: TesterPromptProvider,
) -> None:
    g = _gherkin(
        "get returns product",
        given=["a product exists"],
        when=["I fetch it"],
        then=["I get the product"],
    )
    out = provider.format_user(State(gherkin=g))
    expected = (
        "## get returns product\n\n"
        "```gherkin\n"
        "Given a product exists\n"
        "When I fetch it\n"
        "Then I get the product\n"
        "```"
    )
    assert expected in out


def test_format_user_gherkin_multiple_steps_per_section(
    provider: TesterPromptProvider,
) -> None:
    g = _gherkin(
        "multi",
        given=["a", "b"],
        when=["c", "d"],
        then=["e", "f"],
    )
    out = provider.format_user(State(gherkin=g))
    body = "Given a\nGiven b\nWhen c\nWhen d\nThen e\nThen f"
    assert f"```gherkin\n{body}\n```" in out


def test_format_user_gherkin_empty_steps_still_fenced(
    provider: TesterPromptProvider,
) -> None:
    # All step lists empty → body is empty but the fence remains.
    g = _gherkin("noop", given=[], when=[], then=[])
    out = provider.format_user(State(gherkin=g))
    assert "## noop\n\n```gherkin\n\n```" in out


def test_format_user_gherkin_only_given(
    provider: TesterPromptProvider,
) -> None:
    g = _gherkin("given-only", given=["x"], when=[], then=[])
    out = provider.format_user(State(gherkin=g))
    assert "```gherkin\nGiven x\n```" in out


def test_format_user_gherkin_only_when(
    provider: TesterPromptProvider,
) -> None:
    g = _gherkin("when-only", given=[], when=["y"], then=[])
    out = provider.format_user(State(gherkin=g))
    assert "```gherkin\nWhen y\n```" in out


def test_format_user_gherkin_only_then(
    provider: TesterPromptProvider,
) -> None:
    g = _gherkin("then-only", given=[], when=[], then=["z"])
    out = provider.format_user(State(gherkin=g))
    assert "```gherkin\nThen z\n```" in out


def test_format_user_gherkin_sections_in_given_when_then_order(
    provider: TesterPromptProvider,
) -> None:
    # Lock in the ordering even if the caller's step lists look shuffled.
    g = _gherkin(
        "ordered",
        given=["G1"],
        when=["W1"],
        then=["T1"],
    )
    out = provider.format_user(State(gherkin=g))
    idx_g = out.index("Given G1")
    idx_w = out.index("When W1")
    idx_t = out.index("Then T1")
    assert idx_g < idx_w < idx_t


# ---- format_user: implementer_summary ----


def test_format_user_implementer_summary_verbatim(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_user(State(implementer_summary="I output"))
    assert "Implementer:\nI output" in out


def test_format_user_implementer_summary_is_stripped(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_user(State(implementer_summary="  I output\n\n"))
    # implementer_summary is the last placeholder in the template, so the
    # rendered value has no trailing newline after it.
    assert out.endswith("Implementer:\nI output")
    assert "  I output" not in out


def test_format_user_empty_implementer_summary_rendered_as_none(
    provider: TesterPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Implementer:\n_(none)_" in out


def test_format_user_whitespace_only_implementer_summary_rendered_as_none(
    provider: TesterPromptProvider,
) -> None:
    # implementer_summary is stripped before the truthiness check,
    # so whitespace-only input collapses to _(none)_.
    out = provider.format_user(State(implementer_summary="   \n\t  "))
    assert "Implementer:\n_(none)_" in out


# ---- format_user: template mechanics ----


def test_format_user_uses_configured_user_template() -> None:
    p = TesterPromptProvider(
        system_template="SYS",
        user_template=(
            "TT={target_test_file} TD={target_declaration} "
            "TF={test_function} G={gherkin} D={declares} I={interfaces} "
            "S={sequence} IM={implementer_summary}"
        ),
        final_prompt="F",
    )
    out = p.format_user(State(target_declaration="d"))
    assert out == "TT= TD=d TF= G=_(none)_ D=_(none)_ I=_(none)_ S=_(none)_ IM=_(none)_"


def test_format_user_values_with_braces_are_literal(
    provider: TesterPromptProvider,
) -> None:
    iface = _interface("Repo", content="def f(x: dict = {}): ...")
    seq = _sequence(content="cfg = {}")
    g = _gherkin("bracing", given=["x {y}"], when=[], then=[])
    state = State(
        target_declaration="{decl}",
        interfaces=[iface],
        sequence=seq,
        gherkin=g,
    )
    out = provider.format_user(state)
    assert "TargetDecl: {decl}" in out
    assert "def f(x: dict = {}): ..." in out
    assert "cfg = {}" in out
    assert "Given x {y}" in out


def test_format_user_does_not_reformat_substituted_values(
    provider: TesterPromptProvider,
) -> None:
    # A value that looks like a format token must be preserved verbatim.
    out = provider.format_user(State(target_declaration="{test_function}"))
    assert "TargetDecl: {test_function}" in out


# ---- provider isolation ----


def test_two_providers_do_not_share_state() -> None:
    a = TesterPromptProvider(
        system_template="A",
        user_template=(
            "{target_test_file}|{target_declaration}|{test_function}"
            "|{gherkin}|{declares}|{interfaces}|{sequence}"
            "|{implementer_summary}"
        ),
        final_prompt="FA",
    )
    b = TesterPromptProvider(
        system_template="B",
        user_template="X{test_function}",
        final_prompt="FB",
    )
    out_a = a.format_user(State(test_function="tf"))
    out_b = b.format_user(State(test_function="tf"))
    assert out_a == ("|_(none)_|tf|_(none)_|_(none)_|_(none)_|_(none)_|_(none)_")
    assert out_b == "Xtf"
    assert a.final_user == "FA"
    assert b.final_user == "FB"
