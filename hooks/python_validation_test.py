# hooks/code_validation_test.py

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hooks.python_validation import PythonValidationHook
from models import State, ToolCall

# ---- helpers ----


def _call(
    name: str = "append",
    *,
    path: object = "file.py",
    arguments: dict | None = None,
    call_id: str = "c1",
) -> ToolCall:
    if arguments is None:
        arguments = {"path": path}
    return ToolCall(id=call_id, name=name, arguments=arguments)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def hook(root: Path) -> PythonValidationHook:
    return PythonValidationHook(root=root)


# ---- passthrough: tool name ----


@pytest.mark.parametrize(
    "name",
    ["bash", "cat", "grep", "tree", "write", "read", ""],
)
def test_non_append_patch_tool_passes_through(
    hook: PythonValidationHook, name: str
) -> None:
    call = _call(name=name, path="nope.py")
    result = {"ok": True, "anything": 1}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


@pytest.mark.parametrize(
    "name", ["Append", "APPEND", "Patch", "PATCH", " append", "patch "]
)
def test_tool_name_is_case_sensitive_and_exact(
    hook: PythonValidationHook, name: str
) -> None:
    # `tool_call.name not in ("append", "patch")` is exact, case-sensitive.
    call = _call(name=name)
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


# ---- passthrough: not ok ----


@pytest.mark.parametrize("ok_value", [False, None, 0, "", [], {}])
def test_falsy_ok_passes_through(hook: PythonValidationHook, ok_value: object) -> None:
    call = _call()
    result = {"ok": ok_value}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


def test_missing_ok_key_passes_through(hook: PythonValidationHook) -> None:
    call = _call()
    result = {"anything": 1}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


# ---- passthrough: path invalid ----


def test_missing_path_passes_through(hook: PythonValidationHook) -> None:
    call = _call(arguments={})
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


@pytest.mark.parametrize("bad_path", [None, 42, ["x.py"], {"p": "x.py"}, b"x.py"])
def test_non_string_path_passes_through(
    hook: PythonValidationHook, bad_path: object
) -> None:
    call = _call(path=bad_path)
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


@pytest.mark.parametrize(
    "path", ["file.txt", "file.pyc", "file", "file.md", "file.PY", "file.Py"]
)
def test_non_py_extension_passes_through(hook: PythonValidationHook, path: str) -> None:
    # `endswith(".py")` is case-sensitive: `file.PY` is NOT validated.
    call = _call(path=path)
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


# ---- passthrough: file missing / is dir ----


def test_missing_file_passes_through(hook: PythonValidationHook, root: Path) -> None:
    call = _call(path="ghost.py")
    assert not (root / "ghost.py").exists()
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


def test_directory_named_py_passes_through(
    hook: PythonValidationHook, root: Path
) -> None:
    (root / "dir.py").mkdir()
    call = _call(path="dir.py")
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


# ---- passthrough: outside root ----


def test_relative_traversal_escapes_root(
    hook: PythonValidationHook, root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    outside = tmp_path_factory.mktemp("outside")
    # Broken syntax on purpose: if the hook touched this file, it would
    # flip to ok=False. It must not.
    (outside / "evil.py").write_text("def f(:\n")
    call = _call(path=f"../{outside.name}/evil.py")
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


def test_absolute_path_outside_root(
    hook: PythonValidationHook, root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    outside = tmp_path_factory.mktemp("outside")
    (outside / "evil.py").write_text("def f(:\n")
    call = _call(path=str(outside / "evil.py"))
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


# ---- valid files ----


def test_valid_python_passes_through(hook: PythonValidationHook, root: Path) -> None:
    (root / "ok.py").write_text("x = 1\ndef f():\n    return x\n")
    call = _call(path="ok.py")
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


def test_empty_python_file_passes_through(
    hook: PythonValidationHook, root: Path
) -> None:
    (root / "empty.py").write_text("")
    call = _call(path="empty.py")
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


def test_comments_only_passes_through(hook: PythonValidationHook, root: Path) -> None:
    (root / "comments.py").write_text("# just a comment\n# another\n")
    call = _call(path="comments.py")
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


def test_subdirectory_file_validated(hook: PythonValidationHook, root: Path) -> None:
    (root / "sub").mkdir()
    (root / "sub" / "ok.py").write_text("x = 1\n")
    call = _call(path="sub/ok.py")
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


def test_absolute_path_inside_root_validated(
    hook: PythonValidationHook, root: Path
) -> None:
    (root / "abs.py").write_text("x = 1\n")
    call = _call(path=str(root / "abs.py"))
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


def test_dotdot_inside_root_validated(hook: PythonValidationHook, root: Path) -> None:
    (root / "sub").mkdir()
    (root / "ok.py").write_text("x = 1\n")
    call = _call(path="sub/../ok.py")
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


def test_patch_tool_also_passes_valid_file(
    hook: PythonValidationHook, root: Path
) -> None:
    (root / "ok.py").write_text("x = 1\n")
    call = _call(name="patch", path="ok.py")
    result = {"ok": True}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is result


# ---- syntax errors ----


def test_syntax_error_returns_ok_false(hook: PythonValidationHook, root: Path) -> None:
    (root / "broken.py").write_text("def f(:\n")
    call = _call(path="broken.py")
    out = hook.after_tool_call(state=State(), tool_call=call, result={"ok": True})
    assert out["ok"] is False
    assert out["path"] == "broken.py"
    assert "error" in out


def test_syntax_error_message_matches_format(
    hook: PythonValidationHook, root: Path
) -> None:
    (root / "broken.py").write_text("def f(:\n")
    call = _call(path="broken.py")
    out = hook.after_tool_call(state=State(), tool_call=call, result={"ok": True})
    match = re.fullmatch(r"broken\.py:(\d+): (.+)", out["error"])
    assert match is not None, out["error"]
    assert int(match.group(1)) >= 1
    assert match.group(2).strip()


def test_syntax_error_uses_path_from_arguments(
    hook: PythonValidationHook, root: Path
) -> None:
    (root / "sub").mkdir()
    (root / "sub" / "broken.py").write_text("def f(:\n")
    call = _call(path="sub/broken.py")
    out = hook.after_tool_call(state=State(), tool_call=call, result={"ok": True})
    # `path` and `error` prefix echo the path *from arguments*, not the
    # resolved absolute path.
    assert out["path"] == "sub/broken.py"
    assert out["error"].startswith("sub/broken.py:")


def test_syntax_error_reports_actual_line_number(
    hook: PythonValidationHook, root: Path
) -> None:
    (root / "broken.py").write_text("x = 1\ny = 2\ndef f(:\n")
    call = _call(path="broken.py")
    out = hook.after_tool_call(state=State(), tool_call=call, result={"ok": True})
    assert out["error"].startswith("broken.py:3:")


def test_syntax_error_discards_original_result_fields(
    hook: PythonValidationHook, root: Path
) -> None:
    (root / "broken.py").write_text("def f(:\n")
    call = _call(path="broken.py")
    result = {"ok": True, "extra_field": "should be gone"}
    out = hook.after_tool_call(state=State(), tool_call=call, result=result)
    assert out is not result
    assert set(out.keys()) == {"ok", "path", "error"}
    assert "extra_field" not in out


def test_patch_tool_also_detects_syntax_error(
    hook: PythonValidationHook, root: Path
) -> None:
    (root / "broken.py").write_text("def f(:\n")
    call = _call(name="patch", path="broken.py")
    out = hook.after_tool_call(state=State(), tool_call=call, result={"ok": True})
    assert out["ok"] is False
    assert out["path"] == "broken.py"
