# models/task.py

from __future__ import annotations

from dataclasses import dataclass, field

from models.agent import AgentResult
from models.status import TaskStatus

TaskID = str


@dataclass
class Declaration:
    name: str


@dataclass
class Interface:
    name: str
    language: str
    content: str
    description: str
    steps: list[str]


@dataclass
class Sequence:
    language: str
    content: str


@dataclass
class Gherkin:
    name: str
    target_declaration: str
    given: list[str]
    when: list[str]
    then: list[str]


@dataclass
class Task:
    task_id: TaskID
    goal: str
    target_file: str
    target_test_file: str
    declares: list[Declaration]
    interfaces: list[Interface]
    gherkins: list[Gherkin]
    constitution: str
    sequence: Sequence | None = None


@dataclass
class TaskResult:
    task_id: TaskID
    status: TaskStatus
    results: list[AgentResult] = field(default_factory=list)
