from __future__ import annotations

import re
import subprocess
from pathlib import Path

from models import State, TestResult


class PytestRunner:
    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()

    def test_function(self, state: State) -> str:
        scenario = state["scenario"]
        slug = re.sub(r"[^\w]+", "_", scenario.name).strip("_").lower()
        return f"test_{slug}"

    def run(self, state: State) -> TestResult:
        node_id = f"{Path(state['target_test'])}::{state['test_function']}"
        print(
            f"[test_runner] run cwd={self._root} node={node_id}",
            flush=True,
        )
        proc = subprocess.run(
            ["pytest", "-v", "--tb=short", node_id],
            capture_output=True,
            text=True,
            cwd=self._root,
        )
        output = (proc.stdout + proc.stderr).strip()
        passed = proc.returncode == 0
        print(
            f"[test_runner] result node={node_id} passed={passed} "
            f"returncode={proc.returncode}",
            flush=True,
        )
        return TestResult(passed=passed, output=output)