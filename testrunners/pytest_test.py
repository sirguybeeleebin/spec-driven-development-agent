# testrunners/pytest_test.py

from __future__ import annotations

import subprocess
from pathlib import Path

from testrunners.pytest import PytestRunner


def _runner() -> PytestRunner:
    return PytestRunner(root=Path("/tmp/fake-root"))


def test_test_function_simple():
    assert _runner().test_function("adds two items") == "test_adds_two_items"


def test_test_function_punctuation():
    assert _runner().test_function("Adds (two) items!") == "test_adds_two_items"


def test_test_function_snake():
    assert (
        _runner().test_function("checkout_creates_order")
        == "test_checkout_creates_order"
    )


def test_test_function_has_test_prefix():
    fn = _runner().test_function("some scenario")
    assert fn.startswith("test_")
    assert not fn.endswith("_test")


def test_test_function_strips_leading_trailing_underscores():
    assert _runner().test_function("__some__") == "test_some"


def test_test_function_lowercases():
    assert _runner().test_function("Adds Two Items") == "test_adds_two_items"


def test_run_builds_node_id(monkeypatch):
    captured: list[dict] = []

    def fake_run(cmd, **kwargs):
        captured.append({"cmd": cmd, **kwargs})

        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = _runner()
    result = runner.run(
        target_test="tests/test_shop.py",
        test_function="test_adds_two_items",
    )
    assert result.passed is True
    assert captured[0]["cmd"] == [
        "pytest",
        "-v",
        "--tb=short",
        "tests/test_shop.py::test_adds_two_items",
    ]


def test_run_uses_root_as_cwd(monkeypatch):
    captured: list[dict] = []

    def fake_run(cmd, **kwargs):
        captured.append({"cmd": cmd, **kwargs})

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = PytestRunner(root=Path("/tmp/some-root"))
    runner.run(target_test="x.py", test_function="test_x")
    assert captured[0]["cwd"] == Path("/tmp/some-root")


def test_run_uses_test_function_verbatim(monkeypatch):
    captured: list[dict] = []

    def fake_run(cmd, **kwargs):
        captured.append({"cmd": cmd, **kwargs})

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)
    _runner().run(
        target_test="x.py",
        test_function="custom_explicit_name",
    )
    assert captured[0]["cmd"][-1] == "x.py::custom_explicit_name"


def test_run_uses_target_test_verbatim(monkeypatch):
    captured: list[dict] = []

    def fake_run(cmd, **kwargs):
        captured.append({"cmd": cmd, **kwargs})

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)
    _runner().run(
        target_test="pkg/sub/tests/test_x.py",
        test_function="test_x",
    )
    assert captured[0]["cmd"][-1] == "pkg/sub/tests/test_x.py::test_x"


def test_run_returns_failed_on_nonzero(monkeypatch):
    def fake_run(cmd, **kwargs):
        class R:
            returncode = 1
            stdout = "FAILED"
            stderr = ""

        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _runner().run(target_test="x.py", test_function="test_x")
    assert result.passed is False
    assert "FAILED" in result.output


def test_run_combines_stdout_and_stderr(monkeypatch):
    def fake_run(cmd, **kwargs):
        class R:
            returncode = 1
            stdout = "OUT"
            stderr = "ERR"

        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _runner().run(target_test="x.py", test_function="test_x")
    assert "OUT" in result.output
    assert "ERR" in result.output
