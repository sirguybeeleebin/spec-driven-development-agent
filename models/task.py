from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import NewType


TaskID = NewType("TaskID", str)


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Interface:
    name: str
    content: str


@dataclass
class Scenario:
    name: str
    given: list[str]
    when: list[str]
    then: list[str]


@dataclass
class Task:
    task_id: TaskID
    goal: str
    target: str
    target_test: str
    interfaces: list[Interface]
    scenarios: list[Scenario]
    constitution: str = ""
    activity: str | None = None
    sequence: str | None = None