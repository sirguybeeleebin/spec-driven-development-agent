# tools/bash_test.py

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.bash import ALLOWED_COMMANDS, MAX_LINES, BashTool


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "hello.txt").write_text("line1\nline2\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.txt").write_text("nested\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def tool(workspace: Path) -> BashTool:
    return BashTool(root=workspace)


# ---- schema ----


def test_get_openai_schema_shape(tool: BashTool) -> None:
    schema = tool.get_openai_schema()

    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == "bash"
    assert isinstance(fn["description"], str) and fn["description"]

    params = fn["parameters"]
    assert params["type"] == "object"
    assert set(params["properties"]) == {"command"}
    assert params["required"] == ["command"]


def test_allowed_commands_constant() -> None:
    assert ALLOWED_COMMANDS == frozenset({"ls", "cat", "grep", "head", "sed", "tree"})


def test_schema_description_covers_all_allowed_commands(tool: BashTool) -> None:
    """Every allowlisted command must be documented in the tool description."""
    description = tool.get_openai_schema()["function"]["description"]
    for cmd in ALLOWED_COMMANDS:
        assert f"`{cmd}" in description, f"{cmd!r} missing from description"


# ---- validation of `command` ----


def test_missing_command(tool: BashTool) -> None:
    result = tool.execute({})
    assert result["ok"] is False
    assert result["exit_code"] == -1
    assert "'command' must be a non-empty string" in result["error"]


def test_empty_command(tool: BashTool) -> None:
    result = tool.execute({"command": ""})
    assert result["ok"] is False
    assert result["exit_code"] == -1


def test_whitespace_only_command(tool: BashTool) -> None:
    result = tool.execute({"command": "   "})
    assert result["ok"] is False
    assert result["exit_code"] == -1


def test_non_string_command(tool: BashTool) -> None:
    result = tool.execute({"command": 42})
    assert result["ok"] is False
    assert result["exit_code"] == -1


# ---- allowlist ----


def test_disallowed_command_rm(tool: BashTool) -> None:
    result = tool.execute({"command": "rm -rf /"})
    assert result["ok"] is False
    assert result["exit_code"] == -1
    assert "command not allowed" in result["error"]
    assert "rm" in result["error"]


def test_disallowed_command_echo(tool: BashTool) -> None:
    result = tool.execute({"command": "echo hi"})
    assert result["ok"] is False
    assert "echo" in result["error"]


def test_disallowed_command_python(tool: BashTool) -> None:
    result = tool.execute({"command": "python -c 'print(1)'"})
    assert result["ok"] is False
    assert "python" in result["error"]


def test_disallowed_command_find(tool: BashTool) -> None:
    """`find` is intentionally not allowlisted; only `tree` covers traversal."""
    result = tool.execute({"command": "find . -type f"})
    assert result["ok"] is False
    assert result["exit_code"] == -1
    assert "find" in result["error"]


# ---- allowed commands run ----


def test_ls_lists_directory(tool: BashTool) -> None:
    result = tool.execute({"command": "ls"})
    assert result["ok"] is True
    assert result["exit_code"] == 0
    assert "hello.txt" in result["output"]
    assert "sub" in result["output"]


def test_cat_prints_file(tool: BashTool) -> None:
    result = tool.execute({"command": "cat hello.txt"})
    assert result["ok"] is True
    assert result["output"] == "line1\nline2"


def test_grep_finds_match(tool: BashTool) -> None:
    result = tool.execute({"command": "grep line1 hello.txt"})
    assert result["ok"] is True
    assert result["output"] == "line1"


def test_grep_recursive(tool: BashTool) -> None:
    result = tool.execute({"command": "grep -r nested sub/"})
    assert result["ok"] is True
    assert "nested" in result["output"]


def test_grep_no_match_is_ok(tool: BashTool) -> None:
    result = tool.execute({"command": "grep missing hello.txt"})
    assert result["ok"] is True
    assert result["exit_code"] == 1
    assert result["output"] == ""


def test_head_prints_first_lines(tool: BashTool) -> None:
    result = tool.execute({"command": "head -n 1 hello.txt"})
    assert result["ok"] is True
    assert result["output"] == "line1"


def test_sed_prints_range(tool: BashTool) -> None:
    result = tool.execute({"command": "sed -n 2p hello.txt"})
    assert result["ok"] is True
    assert result["output"] == "line2"


def test_tree_lists_directory_tree(tool: BashTool) -> None:
    result = tool.execute({"command": "tree --noreport ."})
    assert result["ok"] is True
    assert result["exit_code"] == 0
    # Both the top-level file and the nested file should appear in the tree.
    assert "hello.txt" in result["output"]
    assert "nested.txt" in result["output"]


def test_tree_recommended_invocation(tool: BashTool) -> None:
    """The schema-recommended invocation should work end-to-end."""
    result = tool.execute({"command": "tree -L 3 --noreport -I __pycache__ ."})
    assert result["ok"] is True
    assert "hello.txt" in result["output"]


def test_leading_whitespace_still_allowed(tool: BashTool) -> None:
    result = tool.execute({"command": "   ls"})
    assert result["ok"] is True


# ---- error handling from the shell ----


def test_cat_missing_file_fails(tool: BashTool) -> None:
    result = tool.execute({"command": "cat does-not-exist.txt"})
    assert result["ok"] is False
    assert result["exit_code"] != 0
    assert result["error"]


def test_grep_bad_regex_fails(tool: BashTool) -> None:
    result = tool.execute({"command": "grep '[' hello.txt"})
    assert result["ok"] is False
    assert result["exit_code"] != 0
    assert result["error"]


# ---- truncation ----


def test_output_truncation(tmp_path: Path) -> None:
    big = tmp_path / "big.txt"
    big.write_text(
        "\n".join(f"line{i}" for i in range(MAX_LINES + 5)) + "\n",
        encoding="utf-8",
    )
    tool = BashTool(root=tmp_path)
    result = tool.execute({"command": "cat big.txt"})

    assert result["ok"] is True
    assert result["line_count"] == MAX_LINES + 5
    assert result["truncated"] == 5
    assert result["output"].count("\n") == MAX_LINES - 1


def test_output_below_max_not_truncated(tool: BashTool) -> None:
    result = tool.execute({"command": "cat hello.txt"})
    assert result["truncated"] == 0
    assert result["line_count"] == 2


# ---- cwd ----


def test_runs_in_workspace_root(tool: BashTool) -> None:
    result = tool.execute({"command": "cat sub/nested.txt"})
    assert result["ok"] is True
    assert result["output"] == "nested"


# ---- subprocess failure modes ----


def test_timeout_returns_error(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ls", timeout=1)

    monkeypatch.setattr("tools.bash.subprocess.run", fake_run)
    tool = BashTool(root=workspace)
    result = tool.execute({"command": "ls"})

    assert result["ok"] is False
    assert result["exit_code"] == -1
    assert "killed after" in result["error"]


def test_oserror_returns_error(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr("tools.bash.subprocess.run", fake_run)
    tool = BashTool(root=workspace)
    result = tool.execute({"command": "ls"})

    assert result["ok"] is False
    assert result["exit_code"] == -1
    assert "failed to spawn" in result["error"]
