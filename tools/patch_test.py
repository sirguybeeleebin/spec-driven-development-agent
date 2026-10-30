# tools/patch_test.py

from __future__ import annotations

from pathlib import Path

import pytest

from tools.patch import PatchTool


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "file.txt").write_text("hello world", encoding="utf-8")
    return tmp_path


@pytest.fixture
def tool(workspace: Path) -> PatchTool:
    return PatchTool(root=workspace)


# ---- schema ----


def test_get_openai_schema_shape(tool: PatchTool) -> None:
    schema = tool.get_openai_schema()

    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == "patch"
    assert isinstance(fn["description"], str) and fn["description"]

    params = fn["parameters"]
    assert params["type"] == "object"
    assert set(params["properties"]) == {"path", "search", "replace"}
    assert params["required"] == ["path", "search", "replace"]


# ---- happy path ----


def test_execute_replaces_unique_substring(tool: PatchTool, workspace: Path) -> None:
    result = tool.execute({"path": "file.txt", "search": "world", "replace": "there"})
    assert result == {"ok": True, "path": "file.txt", "chars": 11}
    assert (workspace / "file.txt").read_text(encoding="utf-8") == "hello there"


def test_execute_replaces_multiline_block(tool: PatchTool, workspace: Path) -> None:
    (workspace / "code.py").write_text(
        "def a():\n    return 1\n\ndef b():\n    return 2\n",
        encoding="utf-8",
    )
    tool.execute(
        {
            "path": "code.py",
            "search": "def b():\n    return 2\n",
            "replace": "def b():\n    return 3\n",
        }
    )
    assert (workspace / "code.py").read_text(encoding="utf-8") == (
        "def a():\n    return 1\n\ndef b():\n    return 3\n"
    )


def test_execute_replace_with_empty_string(tool: PatchTool, workspace: Path) -> None:
    result = tool.execute({"path": "file.txt", "search": " world", "replace": ""})
    assert result["ok"] is True
    assert (workspace / "file.txt").read_text(encoding="utf-8") == "hello"


def test_execute_chars_field_is_full_file_length(
    tool: PatchTool, workspace: Path
) -> None:
    (workspace / "file.txt").write_text("abcdef", encoding="utf-8")
    result = tool.execute({"path": "file.txt", "search": "cd", "replace": "X"})
    assert result["chars"] == len("abXef")


# ---- search uniqueness ----


def test_execute_rejects_search_not_found(tool: PatchTool) -> None:
    result = tool.execute({"path": "file.txt", "search": "zzz", "replace": "x"})
    assert result["ok"] is False
    assert "search not found" in result["error"]


def test_execute_rejects_ambiguous_search(tool: PatchTool, workspace: Path) -> None:
    (workspace / "file.txt").write_text("aaa", encoding="utf-8")
    result = tool.execute({"path": "file.txt", "search": "a", "replace": "b"})
    assert result["ok"] is False
    assert "search appears 3 times" in result["error"]


def test_execute_rejects_ambiguous_search_keeps_file(
    tool: PatchTool, workspace: Path
) -> None:
    (workspace / "file.txt").write_text("aaa", encoding="utf-8")
    result = tool.execute({"path": "file.txt", "search": "a", "replace": "b"})
    assert result["ok"] is False
    assert (workspace / "file.txt").read_text(encoding="utf-8") == "aaa"


def test_execute_accepts_unique_search_in_repeated_file(
    tool: PatchTool, workspace: Path
) -> None:
    (workspace / "file.txt").write_text("aXa", encoding="utf-8")
    tool.execute({"path": "file.txt", "search": "X", "replace": "Y"})
    assert (workspace / "file.txt").read_text(encoding="utf-8") == "aYa"


# ---- argument validation ----


def test_execute_missing_path(tool: PatchTool) -> None:
    result = tool.execute({"search": "a", "replace": "b"})
    assert result["ok"] is False
    assert "'path' must be a non-empty string" in result["error"]


def test_execute_empty_path(tool: PatchTool) -> None:
    result = tool.execute({"path": "", "search": "a", "replace": "b"})
    assert result["ok"] is False
    assert "'path' must be a non-empty string" in result["error"]


def test_execute_non_string_path(tool: PatchTool) -> None:
    result = tool.execute({"path": 42, "search": "a", "replace": "b"})
    assert result["ok"] is False
    assert "'path' must be a non-empty string" in result["error"]


def test_execute_missing_search(tool: PatchTool) -> None:
    result = tool.execute({"path": "file.txt", "replace": "b"})
    assert result["ok"] is False
    assert "'search' must be a non-empty string" in result["error"]


def test_execute_empty_search(tool: PatchTool) -> None:
    result = tool.execute({"path": "file.txt", "search": "", "replace": "b"})
    assert result["ok"] is False
    assert "'search' must be a non-empty string" in result["error"]


def test_execute_non_string_search(tool: PatchTool) -> None:
    result = tool.execute({"path": "file.txt", "search": 1, "replace": "b"})
    assert result["ok"] is False
    assert "'search' must be a non-empty string" in result["error"]


def test_execute_missing_replace(tool: PatchTool) -> None:
    result = tool.execute({"path": "file.txt", "search": "a"})
    assert result["ok"] is False
    assert "'replace' must be a string" in result["error"]


def test_execute_non_string_replace(tool: PatchTool) -> None:
    result = tool.execute({"path": "file.txt", "search": "a", "replace": 42})
    assert result["ok"] is False
    assert "'replace' must be a string" in result["error"]


# ---- path safety ----


def test_execute_rejects_path_escaping_workspace(tool: PatchTool) -> None:
    result = tool.execute({"path": "../outside.txt", "search": "a", "replace": "b"})
    assert result["ok"] is False
    assert "path escapes workspace" in result["error"]


def test_execute_rejects_absolute_path_outside_workspace(tool: PatchTool) -> None:
    result = tool.execute({"path": "/etc/passwd", "search": "a", "replace": "b"})
    assert result["ok"] is False
    assert "path escapes workspace" in result["error"]


def test_execute_rejects_missing_file(tool: PatchTool) -> None:
    result = tool.execute({"path": "nope.txt", "search": "a", "replace": "b"})
    assert result["ok"] is False
    assert "file not found" in result["error"]


def test_execute_rejects_directory_path(tool: PatchTool, workspace: Path) -> None:
    (workspace / "sub").mkdir()
    result = tool.execute({"path": "sub", "search": "a", "replace": "b"})
    assert result["ok"] is False
    assert "file not found" in result["error"]


# ---- __init__.py creation for .py files ----


def test_execute_creates_init_for_py_file(tool: PatchTool, workspace: Path) -> None:
    pkg = workspace / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("x = 1\n", encoding="utf-8")

    tool.execute({"path": "pkg/mod.py", "search": "1", "replace": "2"})

    assert (pkg / "__init__.py").exists()


def test_execute_does_not_create_init_for_init_py(
    tool: PatchTool, workspace: Path
) -> None:
    pkg = workspace / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("x = 1\n", encoding="utf-8")

    tool.execute({"path": "pkg/__init__.py", "search": "1", "replace": "2"})

    assert (pkg / "__init__.py").read_text(encoding="utf-8") == "x = 2\n"


def test_execute_keeps_existing_init(tool: PatchTool, workspace: Path) -> None:
    pkg = workspace / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("existing\n", encoding="utf-8")
    (pkg / "mod.py").write_text("x = 1\n", encoding="utf-8")

    tool.execute({"path": "pkg/mod.py", "search": "1", "replace": "2"})

    assert (pkg / "__init__.py").read_text(encoding="utf-8") == "existing\n"


def test_execute_does_not_create_init_for_non_py_file(
    tool: PatchTool, workspace: Path
) -> None:
    pkg = workspace / "pkg"
    pkg.mkdir()
    (pkg / "data.txt").write_text("x", encoding="utf-8")

    tool.execute({"path": "pkg/data.txt", "search": "x", "replace": "y"})

    assert not (pkg / "__init__.py").exists()
