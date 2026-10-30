# commands/config_test.py

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from commands import (
    RunConfigClearCommand,
    RunConfigDeleteCommand,
    RunConfigGetCommand,
    RunConfigSetCommand,
)


def _yaml_path(tmp_path: Path) -> Path:
    return tmp_path / "AGENT.yaml"


def config_set_creates_file_test(tmp_path: Path) -> None:
    print(f"[{__name__}] config_set_creates_file_test")
    RunConfigSetCommand(root=tmp_path).execute("model", "gpt-4")
    data = yaml.safe_load(_yaml_path(tmp_path).read_text(encoding="utf-8"))
    assert data == {"model": "gpt-4"}


def config_set_preserves_existing_keys_test(tmp_path: Path) -> None:
    print(f"[{__name__}] config_set_preserves_existing_keys_test")
    _yaml_path(tmp_path).write_text(
        yaml.safe_dump({"model": "old", "temperature": 0.1}),
        encoding="utf-8",
    )
    RunConfigSetCommand(root=tmp_path).execute("model", "new")
    data = yaml.safe_load(_yaml_path(tmp_path).read_text(encoding="utf-8"))
    assert data == {"model": "new", "temperature": 0.1}


def config_set_creates_parent_dir_test(tmp_path: Path) -> None:
    print(f"[{__name__}] config_set_creates_parent_dir_test")
    nested = tmp_path / "deep" / "root"
    RunConfigSetCommand(root=nested).execute("x", "y")
    assert (nested / "AGENT.yaml").exists()


def config_get_returns_value_test(tmp_path: Path) -> None:
    print(f"[{__name__}] config_get_returns_value_test")
    _yaml_path(tmp_path).write_text(
        yaml.safe_dump({"model": "gpt-4"}),
        encoding="utf-8",
    )
    value = RunConfigGetCommand(root=tmp_path).execute("model")
    assert value == "gpt-4"


def config_get_missing_key_raises_test(tmp_path: Path) -> None:
    print(f"[{__name__}] config_get_missing_key_raises_test")
    _yaml_path(tmp_path).write_text(
        yaml.safe_dump({"model": "gpt-4"}),
        encoding="utf-8",
    )
    with pytest.raises(KeyError):
        RunConfigGetCommand(root=tmp_path).execute("nope")


def config_get_missing_file_raises_test(tmp_path: Path) -> None:
    print(f"[{__name__}] config_get_missing_file_raises_test")
    with pytest.raises(KeyError):
        RunConfigGetCommand(root=tmp_path).execute("model")


def config_delete_removes_key_test(tmp_path: Path) -> None:
    print(f"[{__name__}] config_delete_removes_key_test")
    _yaml_path(tmp_path).write_text(
        yaml.safe_dump({"model": "gpt-4", "temperature": 0.2}),
        encoding="utf-8",
    )
    RunConfigDeleteCommand(root=tmp_path).execute("temperature")
    data = yaml.safe_load(_yaml_path(tmp_path).read_text(encoding="utf-8"))
    assert data == {"model": "gpt-4"}


def config_delete_missing_key_raises_test(tmp_path: Path) -> None:
    print(f"[{__name__}] config_delete_missing_key_raises_test")
    with pytest.raises(KeyError):
        RunConfigDeleteCommand(root=tmp_path).execute("nope")


def config_clear_removes_file_test(tmp_path: Path) -> None:
    print(f"[{__name__}] config_clear_removes_file_test")
    _yaml_path(tmp_path).write_text("model: x\n", encoding="utf-8")
    RunConfigClearCommand(root=tmp_path).execute()
    assert not _yaml_path(tmp_path).exists()


def config_clear_missing_file_is_noop_test(tmp_path: Path) -> None:
    print(f"[{__name__}] config_clear_missing_file_is_noop_test")
    RunConfigClearCommand(root=tmp_path).execute()
