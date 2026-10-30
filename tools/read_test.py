# tests/test_read.py

from __future__ import annotations

from pathlib import Path

import pytest

from tools.read import ReadTool


def test_returns_content_and_path(tmp_path: Path):
    target = tmp_path / "a.py"
    target.write_text("x = 1\n", encoding="utf-8")
    tool = ReadTool(root=tmp_path)

    result = tool.execute({"path": "a.py"})

    assert result == {"path": "a.py", "content": "x = 1\n"}
    # ReadTool intentionally does not return "ok" — callers key on
    # absence of "error".
    assert "ok" not in result
    assert "error" not in result


def test_reads_empty_file(tmp_path: Path):
    (tmp_path / "empty.txt").write_text("", encoding="utf-8")
    tool = ReadTool(root=tmp_path)

    result = tool.execute({"path": "empty.txt"})

    assert result["content"] == ""


def test_reads_utf8_content(tmp_path: Path):
    (tmp_path / "a.txt").write_text("Привет\n", encoding="utf-8")
    tool = ReadTool(root=tmp_path)

    result = tool.execute({"path": "a.txt"})

    assert result["content"] == "Привет\n"


def test_reads_nested_path(tmp_path: Path):
    nested = tmp_path / "pkg" / "sub" / "mod.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("y = 2\n", encoding="utf-8")
    tool = ReadTool(root=tmp_path)

    result = tool.execute({"path": "pkg/sub/mod.py"})

    assert result["content"] == "y = 2\n"


def test_raises_when_file_missing(tmp_path: Path):
    tool = ReadTool(root=tmp_path)

    with pytest.raises(ValueError, match="file not found"):
        tool.execute({"path": "nope.py"})


def test_raises_for_directory(tmp_path: Path):
    (tmp_path / "adir").mkdir()
    tool = ReadTool(root=tmp_path)

    # read_text() on a directory raises IsADirectoryError, which is a
    # subclass of OSError, not ValueError. Callers catch Exception.
    with pytest.raises(OSError):
        tool.execute({"path": "adir"})


def test_schema_has_expected_shape(tmp_path: Path):
    tool = ReadTool(root=tmp_path)

    schema = tool.get_openai_schema()

    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == "read"
    assert fn["parameters"]["required"] == ["path"]
    assert set(fn["parameters"]["properties"]) == {"path"}
