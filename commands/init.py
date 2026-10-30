# commands/init.py

from __future__ import annotations

from pathlib import Path

_AGENT_MD = Path("AGENT.md")
_AGENT_YAML = Path("AGENT.yaml")
_SKILLS_DIR = Path("skills")
_TASKS_DIR = Path("tasks")
_WORKFLOWS_DIR = Path("workflows")


class RunInitCommand:
    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()
        self._agent_md = self._root / _AGENT_MD
        self._agent_yaml = self._root / _AGENT_YAML
        self._skills_dir = self._root / _SKILLS_DIR
        self._tasks_dir = self._root / _TASKS_DIR
        self._workflows_dir = self._root / _WORKFLOWS_DIR

    def execute(self) -> list[str]:
        results: list[str] = []
        for p in (self._agent_md, self._agent_yaml):
            if p.exists():
                results.append(f"exists: {p}")
            else:
                results.append(f"missing: {p}")
        for d in (
            self._skills_dir,
            self._tasks_dir,
            self._workflows_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)
            results.append(f"ready: {d}")
        return results
