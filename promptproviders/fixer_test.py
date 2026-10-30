# promptproviders/fixer_test.py

from __future__ import annotations

import pytest

from models import Skill, State
from models.task import Interface
from models.test import TestResult
from promptproviders.fixer import FixerPromptProvider

# If Interface carries additional required fields, or is re-exported via
# models/__init__.py, adjust the import and constructor below — the
# provider only reads ``name`` / ``language`` / ``description`` /
# ``steps`` / ``content`` on interfaces.

SYSTEM = "You are a fixer."
USER_TEMPLATE = (
    "TargetTest: {target_test_file}\n"
    "TargetFile: {target_file}\n"
    "TestFn: {test_function}\n"
    "TestResult:\n{test_result}\n"
    "Interfaces:\n{interfaces}\n"
    "Implementer:\n{implementer_summary}\n"
    "Tester:\n{tester_summary}"
)
FINAL = "Final summary please."


# ---- helpers ----


def _skill(
    name: str,
    description: str = "desc",
    content: str = "",
) -> Skill:
    return Skill(name=name, description=description, content=content)


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


def _result(passed: bool, output: str = "") -> TestResult:
    return TestResult(passed=passed, output=output)


@pytest.fixture
def provider() -> FixerPromptProvider:
    return FixerPromptProvider(
        system_template=SYSTEM,
        user_template=USER_TEMPLATE,
        final_prompt=FINAL,
    )


# ---- format_system ----


def test_format_system_no_skills_returns_template(
    provider: FixerPromptProvider,
) -> None:
    assert provider.format_system([]) == SYSTEM


def test_format_system_with_one_skill(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_system([_skill("alpha", "does alpha")])
    assert out == f"{SYSTEM}\n\n# Skills\n\n- `alpha`: does alpha"


def test_format_system_with_multiple_skills_in_order(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_system([_skill("a", "aa"), _skill("b", "bb")])
    assert out == f"{SYSTEM}\n\n# Skills\n\n- `a`: aa\n- `b`: bb"


def test_format_system_preserves_custom_system() -> None:
    custom = FixerPromptProvider(
        system_template="MY SYS",
        user_template=(
            "{target_test_file}{target_file}{test_function}{test_result}"
            "{interfaces}{implementer_summary}{tester_summary}"
        ),
        final_prompt="F",
    )
    out = custom.format_system([_skill("a", "b")])
    assert out == "MY SYS\n\n# Skills\n\n- `a`: b"


# ---- final_user ----


def test_final_user_returns_configured_string(
    provider: FixerPromptProvider,
) -> None:
    assert provider.final_user == FINAL


def test_final_user_empty_when_configured_empty() -> None:
    p = FixerPromptProvider(
        system_template="",
        user_template=(
            "{target_test_file}{target_file}{test_function}{test_result}"
            "{interfaces}{implementer_summary}{tester_summary}"
        ),
        final_prompt="",
    )
    assert p.final_user == ""


# ---- format_user: empty state defaults ----


def test_format_user_empty_state_uses_none_placeholders(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "TestResult:\n_(none)_" in out
    assert "Interfaces:\n_(none)_" in out
    assert "Implementer:\n_(none)_" in out
    assert "Tester:\n_(none)_" in out


# ---- format_user: scalar fields (no fallback) ----


def test_format_user_target_test_file_verbatim(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(target_test_file="src/x_test.py"))
    assert "TargetTest: src/x_test.py" in out


def test_format_user_empty_target_test_file_stays_empty(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(target_test_file=""))
    assert "TargetTest: \n" in out
    assert "TargetTest: _(none)_" not in out


def test_format_user_target_file_verbatim(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(target_file="src/x.py"))
    assert "TargetFile: src/x.py" in out


def test_format_user_empty_target_file_stays_empty(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(target_file=""))
    assert "TargetFile: \n" in out
    assert "TargetFile: _(none)_" not in out


def test_format_user_test_function_verbatim(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(test_function="test_get"))
    assert "TestFn: test_get" in out


def test_format_user_empty_test_function_stays_empty(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(test_function=""))
    assert "TestFn: \n" in out
    assert "TestFn: _(none)_" not in out


# ---- format_user: test_result ----


def test_format_user_test_result_none_rendered_as_none(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(test_result=None))
    assert "TestResult:\n_(none)_" in out


def test_format_user_test_result_passed(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(test_result=_result(True, output="all good")))
    assert "TestResult:\nStatus: passed\n```\nall good\n```" in out


def test_format_user_test_result_failed(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(
        State(test_result=_result(False, output="assertion error at line 3"))
    )
    assert ("TestResult:\nStatus: failed\n```\nassertion error at line 3\n```") in out


def test_format_user_test_result_empty_output_still_fenced(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(test_result=_result(False, output="")))
    assert "TestResult:\nStatus: failed\n```\n\n```" in out


def test_format_user_test_result_multiline_output_preserved(
    provider: FixerPromptProvider,
) -> None:
    output = "line 1\nline 2\nline 3"
    out = provider.format_user(State(test_result=_result(False, output=output)))
    assert f"Status: failed\n```\n{output}\n```" in out


def test_format_user_test_result_output_not_stripped(
    provider: FixerPromptProvider,
) -> None:
    # test_result.output is passed through verbatim — no strip.
    out = provider.format_user(State(test_result=_result(False, output="  spaced  ")))
    assert "Status: failed\n```\n  spaced  \n```" in out


def test_format_user_test_result_output_with_braces_is_literal(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(
        State(test_result=_result(False, output="def f(x: dict = {}): ..."))
    )
    assert "def f(x: dict = {}): ..." in out


# ---- format_user: interfaces ----


def test_format_user_interface_minimal_block(
    provider: FixerPromptProvider,
) -> None:
    iface = _interface("Repo", language="python", content="class Repo: pass")
    out = provider.format_user(State(interfaces=[iface]))
    assert "## Interface: Repo" in out
    assert "Language: python" in out
    assert "Description:" not in out
    assert "Steps:" not in out
    assert "```python\nclass Repo: pass\n```" in out


def test_format_user_interface_with_description(
    provider: FixerPromptProvider,
) -> None:
    iface = _interface("Repo", description="a repository pattern", content="pass")
    out = provider.format_user(State(interfaces=[iface]))
    assert "Description: a repository pattern" in out


def test_format_user_interface_with_steps(
    provider: FixerPromptProvider,
) -> None:
    iface = _interface("Repo", steps=["open", "read", "close"], content="pass")
    out = provider.format_user(State(interfaces=[iface]))
    assert "Steps:\n1. open\n2. read\n3. close" in out


def test_format_user_interface_full_block(
    provider: FixerPromptProvider,
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
    provider: FixerPromptProvider,
) -> None:
    a = _interface("A", content="a")
    b = _interface("B", content="b")
    out = provider.format_user(State(interfaces=[a, b]))
    assert "```python\na\n```\n\n## Interface: B" in out


def test_format_user_empty_interfaces_rendered_as_none(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Interfaces:\n_(none)_" in out


def test_format_user_interface_empty_language(
    provider: FixerPromptProvider,
) -> None:
    iface = _interface("X", language="", content="hi")
    out = provider.format_user(State(interfaces=[iface]))
    assert "## Interface: X\n\nLanguage: \n\n```\nhi\n```" in out


# ---- format_user: implementer_summary ----


def test_format_user_implementer_summary_verbatim(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(implementer_summary="I output"))
    assert "Implementer:\nI output" in out


def test_format_user_implementer_summary_is_stripped(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(implementer_summary="  I output\n\n"))
    # implementer_summary is not the last placeholder, so a trailing
    # newline is present here — but the value itself is stripped.
    assert "Implementer:\nI output\n" in out
    assert "  I output" not in out


def test_format_user_empty_implementer_summary_rendered_as_none(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Implementer:\n_(none)_" in out


def test_format_user_whitespace_only_implementer_summary_rendered_as_none(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(implementer_summary="   \n\t  "))
    assert "Implementer:\n_(none)_" in out


# ---- format_user: tester_summary ----


def test_format_user_tester_summary_verbatim(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(tester_summary="T output"))
    assert "Tester:\nT output" in out


def test_format_user_tester_summary_is_stripped(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(tester_summary="  T output\n\n"))
    # tester_summary is the last placeholder in the template, so the
    # rendered value has no trailing newline after it.
    assert out.endswith("Tester:\nT output")
    assert "  T output" not in out


def test_format_user_empty_tester_summary_rendered_as_none(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State())
    assert "Tester:\n_(none)_" in out


def test_format_user_whitespace_only_tester_summary_rendered_as_none(
    provider: FixerPromptProvider,
) -> None:
    out = provider.format_user(State(tester_summary="   \n\t  "))
    assert "Tester:\n_(none)_" in out


# ---- format_user: template mechanics ----


def test_format_user_uses_configured_user_template() -> None:
    p = FixerPromptProvider(
        system_template="SYS",
        user_template=(
            "TT={target_test_file} TF={target_file} FN={test_function} "
            "TR={test_result} I={interfaces} "
            "IM={implementer_summary} TS={tester_summary}"
        ),
        final_prompt="F",
    )
    out = p.format_user(State(target_file="x.py"))
    assert out == "TT= TF=x.py FN= TR=_(none)_ I=_(none)_ IM=_(none)_ TS=_(none)_"


def test_format_user_does_not_reformat_substituted_values(
    provider: FixerPromptProvider,
) -> None:
    # A value that looks like a format token must be preserved verbatim.
    out = provider.format_user(State(target_file="{test_function}"))
    assert "TargetFile: {test_function}" in out


def test_format_user_values_with_braces_are_literal(
    provider: FixerPromptProvider,
) -> None:
    iface = _interface("Repo", content="def f(x: dict = {}): ...")
    state = State(
        target_file="{tf}",
        interfaces=[iface],
        test_result=_result(False, output="cfg = {}"),
    )
    out = provider.format_user(state)
    assert "TargetFile: {tf}" in out
    assert "def f(x: dict = {}): ..." in out
    assert "cfg = {}" in out


# ---- provider isolation ----


def test_two_providers_do_not_share_state() -> None:
    a = FixerPromptProvider(
        system_template="A",
        user_template=(
            "{target_test_file}|{target_file}|{test_function}|{test_result}"
            "|{interfaces}|{implementer_summary}|{tester_summary}"
        ),
        final_prompt="FA",
    )
    b = FixerPromptProvider(
        system_template="B",
        user_template="X{target_file}",
        final_prompt="FB",
    )
    out_a = a.format_user(State(target_file="f.py"))
    out_b = b.format_user(State(target_file="f.py"))
    assert out_a == ("|f.py||_(none)_|_(none)_|_(none)_|_(none)_")
    assert out_b == "Xf.py"
    assert a.final_user == "FA"
    assert b.final_user == "FB"
