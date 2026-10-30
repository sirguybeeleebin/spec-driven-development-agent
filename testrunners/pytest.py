# testrunners/pytest.py

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from models import State, TestResult


class PytestRunner:
    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()

    def test_function(self, state: State) -> str:
        if state.gherkin is None:
            raise ValueError(
                "pytest runner: state.gherkin is None; "
                "cannot derive a test function name"
            )
        slug = re.sub(r"[^\w]+", "_", state.gherkin.name).strip("_").lower()
        return f"test_{slug}"

    def run(self, state: State) -> TestResult:
        if not state.target_test_file:
            raise ValueError("pytest runner: state.target_test_file is empty")
        if not state.test_function:
            raise ValueError("pytest runner: state.test_function is empty")

        node_id = f"{state.target_test_file}::{state.test_function}"
        proc = subprocess.run(
            ["pytest", "-v", "--tb=short", node_id],
            capture_output=True,
            text=True,
            cwd=self._root,
        )
        output = (proc.stdout + proc.stderr).strip()
        passed = proc.returncode == 0

        return TestResult(passed=passed, output=output)
