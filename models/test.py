# models/test.py

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TestResult:
    passed: bool
    output: str
