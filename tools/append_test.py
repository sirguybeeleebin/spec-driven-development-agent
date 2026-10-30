# tools/append_test.py

from __future__ import annotations

from pathlib import Path

import pytest

from tools.append import AppendTool


@pytest.fixture
def tool(tmp_path: Path) -> AppendTool:
    return AppendTool(root=tmp_path)


# ---- schema ----


def test_get_openai_schema_shape(tool: AppendTool) -> None:
    schema = tool.get_openai_schema()

    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == "append"
    assert isinstance(fn["description"], str) and fn["description"]

    params = fn["parameters"]
    assert params["type"] == "object"
    assert set(params["properties"]) == {"path", "content"}
    assert params["required"] == ["path", "content"]


# ---- happy path ----


def test_execute_creates_new_file(tool: AppendTool, tmp_path: Path) -> None:
    result = tool.execute({"path": "note.txt", "content": "hello"})

    assert result == {"ok": True, "path": "note.txt", "chars": 5}
    assert (tmp_path / "note.txt").read_text(encoding="utf-8") == "hello"


def test_execute_creates_parent_directories(tool: AppendTool, tmp_path: Path) -> None:
    tool.execute({"path": "a/b/c/note.txt", "content": "x"})

    assert (tmp_path / "a" / "b" / "c" / "note.txt").read_text(encoding="utf-8") == "x"


def test_execute_appends_to_existing_file_with_newline(
    tool: AppendTool, tmp_path: Path
) -> None:
    (tmp_path / "log.txt").write_text("first\n", encoding="utf-8")
    tool.execute({"path": "log.txt", "content": "second\n"})

    assert (tmp_path / "log.txt").read_text(encoding="utf-8") == "first\nsecond\n"


def test_execute_inserts_newline_when_existing_file_missing_one(
    tool: AppendTool, tmp_path: Path
) -> None:
    (tmp_path / "log.txt").write_text("first", encoding="utf-8")
    tool.execute({"path": "log.txt", "content": "second"})

    assert (tmp_path / "log.txt").read_text(encoding="utf-8") == "first\nsecond"


def test_execute_does_not_insert_newline_on_empty_file(
    tool: AppendTool, tmp_path: Path
) -> None:
    (tmp_path / "log.txt").write_text("", encoding="utf-8")
    tool.execute({"path": "log.txt", "content": "hello"})

    assert (tmp_path / "log.txt").read_text(encoding="utf-8") == "hello"


def test_execute_supports_multiple_appends(tool: AppendTool, tmp_path: Path) -> None:
    tool.execute({"path": "log.txt", "content": "a\n"})
    tool.execute({"path": "log.txt", "content": "b\n"})

    assert (tmp_path / "log.txt").read_text(encoding="utf-8") == "a\nb\n"


# ---- __init__.py creation ----


def test_execute_creates_init_for_py_file(tool: AppendTool, tmp_path: Path) -> None:
    tool.execute({"path": "pkg/mod.py", "content": "x = 1\n"})

    assert (tmp_path / "pkg" / "__init__.py").exists()
    assert (tmp_path / "pkg" / "mod.py").read_text(encoding="utf-8") == "x = 1\n"


def test_execute_does_not_create_init_for_init_py(
    tool: AppendTool, tmp_path: Path
) -> None:
    tool.execute({"path": "pkg/__init__.py", "content": "x = 1\n"})

    assert (tmp_path / "pkg" / "__init__.py").read_text(encoding="utf-8") == "x = 1\n"


def test_execute_keeps_existing_init(tool: AppendTool, tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("existing\n", encoding="utf-8")

    tool.execute({"path": "pkg/mod.py", "content": "x = 1\n"})

    assert (pkg / "__init__.py").read_text(encoding="utf-8") == "existing\n"


def test_execute_does_not_create_init_for_non_py_file(
    tool: AppendTool, tmp_path: Path
) -> None:
    tool.execute({"path": "pkg/data.txt", "content": "x"})

    assert not (tmp_path / "pkg" / "__init__.py").exists()


# ---- argument validation ----


def test_execute_rejects_empty_path(tool: AppendTool) -> None:
    result = tool.execute({"path": "", "content": "x"})
    assert result["ok"] is False
    assert "'path' must be a non-empty string" in result["error"]


def test_execute_rejects_non_string_path(tool: AppendTool) -> None:
    result = tool.execute({"path": 42, "content": "x"})
    assert result["ok"] is False
    assert "'path' must be a non-empty string" in result["error"]


def test_execute_rejects_missing_path(tool: AppendTool) -> None:
    result = tool.execute({"content": "x"})
    assert result["ok"] is False
    assert "'path' must be a non-empty string" in result["error"]


def test_execute_rejects_non_string_content(tool: AppendTool) -> None:
    result = tool.execute({"path": "f.txt", "content": 42})
    assert result["ok"] is False
    assert "'content' must be a string" in result["error"]


def test_execute_rejects_missing_content(tool: AppendTool) -> None:
    result = tool.execute({"path": "f.txt"})
    assert result["ok"] is False
    assert "'content' must be a string" in result["error"]


# ---- path safety ----


def test_execute_rejects_path_escaping_workspace(tool: AppendTool) -> None:
    result = tool.execute({"path": "../outside.txt", "content": "x"})
    assert result["ok"] is False
    assert "path escapes workspace" in result["error"]


def test_execute_rejects_absolute_path_outside_workspace(tool: AppendTool) -> None:
    result = tool.execute({"path": "/tmp/outside.txt", "content": "x"})
    assert result["ok"] is False
    assert "path escapes workspace" in result["error"]
