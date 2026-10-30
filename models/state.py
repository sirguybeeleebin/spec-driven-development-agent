# models/state.py

from __future__ import annotations

from dataclasses import dataclass, field

from models.task import Declaration, Gherkin, Interface, Sequence
from models.test import TestResult


@dataclass
class State:
    goal: str = ""
    target_file: str = ""
    target_test_file: str = ""
    target_declaration: str = ""
    test_function: str = ""
    declares: list[Declaration] = field(default_factory=list)
    interfaces: list[Interface] = field(default_factory=list)
    gherkin: Gherkin | None = None
    constitution: str = ""
    sequence: Sequence | None = None
    researcher_summary: str = ""
    implementer_summary: str = ""
    tester_summary: str = ""
    test_result: TestResult | None = None
