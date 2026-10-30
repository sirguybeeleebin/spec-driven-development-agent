# app/config_test.py

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.config import load_config, load_constitution, load_task


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


# ---- load_config ----


def test_load_config_missing_raises(root: Path) -> None:
    with pytest.raises(FileNotFoundError, match="config not found"):
        load_config(root)


def test_load_config_missing_message_includes_path(root: Path) -> None:
    with pytest.raises(FileNotFoundError) as exc:
        load_config(root)
    assert "AGENT.yaml" in str(exc.value)


def test_load_config_empty_file_returns_empty_dict(root: Path) -> None:
    (root / "AGENT.yaml").write_text("")
    assert load_config(root) == {}


def test_load_config_returns_parsed_yaml(root: Path) -> None:
    (root / "AGENT.yaml").write_text("agents:\n  researcher:\n    x: 1\n")
    assert load_config(root) == {"agents": {"researcher": {"x": 1}}}


def test_load_config_parses_full_config(root: Path) -> None:
    payload = {
        "agents": {
            "researcher": {"provider": {"model": "m", "temperature": 0.5}},
            "implementer": {},
        }
    }
    (root / "AGENT.yaml").write_text(yaml.safe_dump(payload))
    data = load_config(root)
    assert data == payload


def test_load_config_ignores_non_agents_keys(root: Path) -> None:
    (root / "AGENT.yaml").write_text("other: 1\nagents:\n  a: {}\n")
    assert load_config(root) == {"other": 1, "agents": {"a": {}}}


# ---- load_constitution ----


def test_load_constitution_missing_returns_empty(root: Path) -> None:
    assert load_constitution(root) == ""


def test_load_constitution_returns_content(root: Path) -> None:
    (root / "AGENT.md").write_text("Be nice.\n")
    assert load_constitution(root) == "Be nice.\n"


def test_load_constitution_preserves_whitespace(root: Path) -> None:
    content = "  leading\n\ntrailing  \n"
    (root / "AGENT.md").write_text(content)
    assert load_constitution(root) == content


def test_load_constitution_empty_file_returns_empty(root: Path) -> None:
    (root / "AGENT.md").write_text("")
    assert load_constitution(root) == ""


# ---- load_task ----


def test_load_task_missing_raises(root: Path) -> None:
    with pytest.raises(FileNotFoundError, match="task file not found"):
        load_task(root, "t1")


def test_load_task_missing_message_includes_path(root: Path) -> None:
    with pytest.raises(FileNotFoundError) as exc:
        load_task(root, "missing")
    msg = str(exc.value)
    assert "tasks" in msg
    assert "missing.md" in msg


def test_load_task_returns_content(root: Path) -> None:
    (root / "tasks").mkdir()
    body = "# Task\n- task_id: t1\n"
    (root / "tasks" / "t1.md").write_text(body)
    assert load_task(root, "t1") == body


def test_load_task_does_not_create_tasks_directory(root: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_task(root, "x")
    assert not (root / "tasks").exists()


def test_load_task_preserves_whitespace(root: Path) -> None:
    (root / "tasks").mkdir()
    content = "  padded\n\nbody\n"
    (root / "tasks" / "t.md").write_text(content)
    assert load_task(root, "t") == content


def test_load_task_nested_task_id_raises(root: Path) -> None:
    # `task_id` with slash points into a subdirectory that doesn't exist.
    (root / "tasks").mkdir()
    with pytest.raises(FileNotFoundError):
        load_task(root, "sub/evil")
