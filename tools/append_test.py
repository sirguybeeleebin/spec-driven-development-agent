# tools/append_test.py

from __future__ import annotations

from pathlib import Path

import pytest

from tools.append import AppendTool


def test_creates_missing_file(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    result = tool.execute({"path": "a.py", "content": "print('hi')\n"})

    assert result["ok"] is True
    assert result["path"] == "a.py"
    assert result["chars"] == 12
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "print('hi')\n"


def test_creates_missing_parent_directories(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    tool.execute({"path": "pkg/sub/mod.py", "content": "x = 1\n"})

    assert (tmp_path / "pkg" / "sub" / "mod.py").is_file()


def test_appends_to_existing_file(tmp_path: Path):
    target = tmp_path / "a.txt"
    target.write_text("one\n", encoding="utf-8")
    tool = AppendTool(root=tmp_path)

    tool.execute({"path": "a.txt", "content": "two\n"})

    assert target.read_text(encoding="utf-8") == "one\ntwo\n"


def test_multiple_appends_accumulate_in_order(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    tool.execute({"path": "a.txt", "content": "a"})
    tool.execute({"path": "a.txt", "content": "b"})
    tool.execute({"path": "a.txt", "content": "c"})

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "a\nb\nc\n"


def test_writes_utf8_content(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    tool.execute({"path": "a.txt", "content": "Привет, мир\n"})

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "Привет, мир\n"


def test_schema_has_expected_shape(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    schema = tool.get_openai_schema()

    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == "append"
    assert fn["parameters"]["required"] == ["path", "content"]
    assert set(fn["parameters"]["properties"]) == {"path", "content"}


def test_root_is_resolved_to_absolute_path(tmp_path: Path):
    tool = AppendTool(root=tmp_path / ".")

    tool.execute({"path": "x.txt", "content": "y"})

    assert (tmp_path / "x.txt").read_text(encoding="utf-8") == "y\n"


def test_missing_content_raises_value_error(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    with pytest.raises(ValueError, match="'content' must be a string"):
        tool.execute({"path": "a.txt"})


def test_missing_path_raises_value_error(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    with pytest.raises(ValueError, match="'path' must be a string"):
        tool.execute({"content": "x"})


def test_non_string_path_raises_value_error(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    with pytest.raises(ValueError, match="'path' must be a string"):
        tool.execute({"path": 123, "content": "x"})


def test_non_string_content_raises_value_error(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    with pytest.raises(ValueError, match="'content' must be a string"):
        tool.execute({"path": "a.py", "content": 123})


def test_adds_trailing_newline_when_missing(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    tool.execute({"path": "a.txt", "content": "hello"})

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hello\n"


def test_adds_separator_newline_between_appends(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    tool.execute({"path": "a.txt", "content": "line1"})
    tool.execute({"path": "a.txt", "content": "line2"})

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "line1\nline2\n"


def test_does_not_duplicate_newline_when_present(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    tool.execute({"path": "a.txt", "content": "line1\n"})
    tool.execute({"path": "a.txt", "content": "line2\n"})

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "line1\nline2\n"


def test_two_appends_produce_valid_python(tmp_path: Path):
    tool = AppendTool(root=tmp_path)

    tool.execute(
        {
            "path": "t.py",
            "content": "def test_a():\n    assert True\n",
        }
    )
    tool.execute(
        {
            "path": "t.py",
            "content": "def test_b():\n    assert True\n",
        }
    )

    text = (tmp_path / "t.py").read_text(encoding="utf-8")
    compile(text, "t.py", "exec")
