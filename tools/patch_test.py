# tests/test_patch.py

from __future__ import annotations

from pathlib import Path

import pytest

from tools.patch import PatchTool


def test_replaces_single_occurrence(tmp_path: Path):
    target = tmp_path / "a.py"
    target.write_text("x = 1\ny = 2\n", encoding="utf-8")
    tool = PatchTool(root=tmp_path)

    result = tool.execute({"path": "a.py", "search": "x = 1", "replace": "x = 42"})

    assert result == {"ok": True, "path": "a.py"}
    assert target.read_text(encoding="utf-8") == "x = 42\ny = 2\n"


def test_replaces_only_first_of_several_is_ambiguous(tmp_path: Path):
    # The tool refuses any search that matches more than once.
    target = tmp_path / "a.py"
    target.write_text("foo\nfoo\n", encoding="utf-8")
    tool = PatchTool(root=tmp_path)

    with pytest.raises(ValueError, match="ambiguous"):
        tool.execute({"path": "a.py", "search": "foo", "replace": "bar"})

    assert target.read_text(encoding="utf-8") == "foo\nfoo\n"


def test_raises_when_file_missing(tmp_path: Path):
    tool = PatchTool(root=tmp_path)

    with pytest.raises(ValueError, match="file not found"):
        tool.execute({"path": "nope.py", "search": "a", "replace": "b"})


def test_raises_when_search_missing(tmp_path: Path):
    target = tmp_path / "a.py"
    target.write_text("hello\n", encoding="utf-8")
    tool = PatchTool(root=tmp_path)

    with pytest.raises(ValueError, match="search not found"):
        tool.execute({"path": "a.py", "search": "world", "replace": "x"})


def test_leaves_file_unchanged_on_ambiguous_error(tmp_path: Path):
    original = "abc\nabc\nabc\n"
    target = tmp_path / "a.txt"
    target.write_text(original, encoding="utf-8")
    tool = PatchTool(root=tmp_path)

    with pytest.raises(ValueError):
        tool.execute({"path": "a.txt", "search": "abc", "replace": "z"})

    assert target.read_text(encoding="utf-8") == original


def test_multiline_search(tmp_path: Path):
    target = tmp_path / "a.py"
    target.write_text("a\nb\nc\n", encoding="utf-8")
    tool = PatchTool(root=tmp_path)

    tool.execute({"path": "a.py", "search": "a\nb\n", "replace": "X\n"})

    assert target.read_text(encoding="utf-8") == "X\nc\n"


def test_preserves_utf8_content(tmp_path: Path):
    target = tmp_path / "a.txt"
    target.write_text("привет мир\n", encoding="utf-8")
    tool = PatchTool(root=tmp_path)

    tool.execute({"path": "a.txt", "search": "мир", "replace": "земля"})

    assert target.read_text(encoding="utf-8") == "привет земля\n"


def test_schema_has_expected_shape(tmp_path: Path):
    tool = PatchTool(root=tmp_path)

    schema = tool.get_openai_schema()

    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == "patch"
    assert set(fn["parameters"]["required"]) == {"path", "search", "replace"}
    assert set(fn["parameters"]["properties"]) == {
        "path",
        "search",
        "replace",
    }
