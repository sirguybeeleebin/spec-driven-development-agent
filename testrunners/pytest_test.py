# testrunners/pytest_test.py

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from models import Gherkin, State
from testrunners.pytest import PytestRunner


def _gherkin(name: str) -> Gherkin:
    return Gherkin(
        name=name,
        target_declaration="X",
        given=["g"],
        when=["w"],
        then=["t"],
    )


@pytest.fixture
def tool(tmp_path: Path) -> PytestRunner:
    return PytestRunner(root=tmp_path)


def _fake_completed(returncode: int, stdout: str = "", stderr: str = ""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


# ---- test_function: slug derivation ----


def test_test_function_lowercases_and_replaces_spaces(tool: PytestRunner) -> None:
    state = State(gherkin=_gherkin("get returns product"))
    assert tool.test_function(state) == "test_get_returns_product"


def test_test_function_lowercases_uppercase_input(tool: PytestRunner) -> None:
    state = State(gherkin=_gherkin("Get Returns Product"))
    assert tool.test_function(state) == "test_get_returns_product"


def test_test_function_replaces_punctuation(tool: PytestRunner) -> None:
    state = State(gherkin=_gherkin("insert with unknown reference!"))
    assert tool.test_function(state) == "test_insert_with_unknown_reference"


def test_test_function_collapses_multiple_non_word_runs(tool: PytestRunner) -> None:
    state = State(gherkin=_gherkin("one...two---three"))
    assert tool.test_function(state) == "test_one_two_three"


def test_test_function_strips_leading_and_trailing_separators(
    tool: PytestRunner,
) -> None:
    state = State(gherkin=_gherkin("  foo  "))
    assert tool.test_function(state) == "test_foo"


def test_test_function_keeps_digits_and_underscores(tool: PytestRunner) -> None:
    state = State(gherkin=_gherkin("scenario_42 works"))
    assert tool.test_function(state) == "test_scenario_42_works"


def test_test_function_handles_unicode_letters(tool: PytestRunner) -> None:
    state = State(gherkin=_gherkin("привет мир"))
    assert tool.test_function(state) == "test_привет_мир"


def test_test_function_empty_name_yields_test_underscore(tool: PytestRunner) -> None:
    state = State(gherkin=_gherkin(""))
    assert tool.test_function(state) == "test_"


def test_test_function_only_punctuation_yields_test_underscore(
    tool: PytestRunner,
) -> None:
    state = State(gherkin=_gherkin("!!!"))
    assert tool.test_function(state) == "test_"


def test_test_function_only_underscores_yields_test_underscore(
    tool: PytestRunner,
) -> None:
    state = State(gherkin=_gherkin("___"))
    assert tool.test_function(state) == "test_"


# ---- test_function: missing gherkin ----


def test_test_function_raises_when_gherkin_is_none(tool: PytestRunner) -> None:
    state = State()
    with pytest.raises(ValueError, match="state.gherkin is None"):
        tool.test_function(state)


# ---- run: argument validation ----


def test_run_raises_on_empty_target_test_file(tool: PytestRunner) -> None:
    state = State(target_test_file="", test_function="test_foo")
    with pytest.raises(ValueError, match="state.target_test_file is empty"):
        tool.run(state)


def test_run_raises_on_empty_test_function(tool: PytestRunner) -> None:
    state = State(target_test_file="a_test.py", test_function="")
    with pytest.raises(ValueError, match="state.test_function is empty"):
        tool.run(state)


# ---- run: subprocess invocation ----


def test_run_builds_node_id_from_fields(
    tool: PytestRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list = []

    def fake_run(*args, **kwargs):
        captured.append((args, kwargs))
        return _fake_completed(0, stdout="ok\n")

    monkeypatch.setattr("testrunners.pytest.subprocess.run", fake_run)

    state = State(target_test_file="pkg/mod_test.py", test_function="test_a")
    tool.run(state)

    call_args, call_kwargs = captured[0]
    assert call_args[0] == [
        "pytest",
        "-v",
        "--tb=short",
        "pkg/mod_test.py::test_a",
    ]
    assert call_kwargs["capture_output"] is True
    assert call_kwargs["text"] is True
    assert Path(call_kwargs["cwd"]) == tool._root


def test_run_passes_resolved_root_as_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "sub").mkdir()
    root = tmp_path / "sub"
    tool = PytestRunner(root=root)

    captured: list = []

    def fake_run(*args, **kwargs):
        captured.append(kwargs)
        return _fake_completed(0)

    monkeypatch.setattr("testrunners.pytest.subprocess.run", fake_run)

    tool.run(State(target_test_file="x_test.py", test_function="test_x"))
    assert Path(captured[0]["cwd"]) == root.resolve()


# ---- run: result mapping ----


def test_run_returns_passed_true_on_zero_exit(
    tool: PytestRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "testrunners.pytest.subprocess.run",
        lambda *a, **kw: _fake_completed(0, stdout="1 passed\n", stderr=""),
    )
    result = tool.run(State(target_test_file="a_test.py", test_function="test_a"))
    assert result.passed is True


def test_run_returns_passed_false_on_nonzero_exit(
    tool: PytestRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "testrunners.pytest.subprocess.run",
        lambda *a, **kw: _fake_completed(1, stdout="1 failed\n", stderr=""),
    )
    result = tool.run(State(target_test_file="a_test.py", test_function="test_a"))
    assert result.passed is False


def test_run_merges_stdout_and_stderr(
    tool: PytestRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "testrunners.pytest.subprocess.run",
        lambda *a, **kw: _fake_completed(1, stdout="out\n", stderr="err\n"),
    )
    result = tool.run(State(target_test_file="a_test.py", test_function="test_a"))
    assert "out" in result.output
    assert "err" in result.output


def test_run_strips_surrounding_whitespace(
    tool: PytestRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "testrunners.pytest.subprocess.run",
        lambda *a, **kw: _fake_completed(0, stdout="\n\n   body   \n\n", stderr=""),
    )
    result = tool.run(State(target_test_file="a_test.py", test_function="test_a"))
    assert result.output == "body"


def test_run_empty_output_stays_empty(
    tool: PytestRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "testrunners.pytest.subprocess.run",
        lambda *a, **kw: _fake_completed(0, stdout="", stderr=""),
    )
    result = tool.run(State(target_test_file="a_test.py", test_function="test_a"))
    assert result.output == ""
    assert result.passed is True


def test_run_preserves_multiline_output(
    tool: PytestRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = "line1\nline2\nline3"
    monkeypatch.setattr(
        "testrunners.pytest.subprocess.run",
        lambda *a, **kw: _fake_completed(1, stdout=body, stderr=""),
    )
    result = tool.run(State(target_test_file="a_test.py", test_function="test_a"))
    assert result.output == body


# ---- run: subprocess failure propagates ----


def test_run_propagates_oserror_from_subprocess(
    tool: PytestRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args, **kwargs):
        raise OSError("pytest not found")

    monkeypatch.setattr("testrunners.pytest.subprocess.run", boom)

    with pytest.raises(OSError, match="pytest not found"):
        tool.run(State(target_test_file="a_test.py", test_function="test_a"))
