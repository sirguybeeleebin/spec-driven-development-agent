# commands/config.py

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_AGENT_YAML = Path("AGENT.yaml")


class RunConfigSetCommand:
    def __init__(self, *, root: Path) -> None:
        self._agent_yaml = root.resolve() / _AGENT_YAML

    def execute(self, key: str, value: str) -> None:
        data: dict[str, Any] = {}
        if self._agent_yaml.exists():
            with self._agent_yaml.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        data[key] = value
        self._agent_yaml.parent.mkdir(parents=True, exist_ok=True)
        self._agent_yaml.write_text(
            yaml.safe_dump(data, sort_keys=False),
            encoding="utf-8",
        )


class RunConfigGetCommand:
    def __init__(self, *, root: Path) -> None:
        self._agent_yaml = root.resolve() / _AGENT_YAML

    def execute(self, key: str) -> str:
        data: dict[str, Any] = {}
        if self._agent_yaml.exists():
            with self._agent_yaml.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        if key not in data:
            raise KeyError(key)
        return str(data[key])


class RunConfigDeleteCommand:
    def __init__(self, *, root: Path) -> None:
        self._agent_yaml = root.resolve() / _AGENT_YAML

    def execute(self, key: str) -> None:
        data: dict[str, Any] = {}
        if self._agent_yaml.exists():
            with self._agent_yaml.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        if key not in data:
            raise KeyError(key)
        del data[key]
        self._agent_yaml.write_text(
            yaml.safe_dump(data, sort_keys=False),
            encoding="utf-8",
        )


class RunConfigClearCommand:
    def __init__(self, *, root: Path) -> None:
        self._agent_yaml = root.resolve() / _AGENT_YAML

    def execute(self) -> None:
        if self._agent_yaml.exists():
            self._agent_yaml.unlink()
