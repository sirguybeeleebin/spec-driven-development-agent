# app/config.py

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(root: Path) -> dict[str, Any]:
    path = root / "AGENT.yaml"
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_constitution(root: Path) -> str:
    path = root / "AGENT.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_task(root: Path, task_id: str) -> str:
    path = (root / "tasks") / f"{task_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"task file not found: {path}")
    return path.read_text(encoding="utf-8")
