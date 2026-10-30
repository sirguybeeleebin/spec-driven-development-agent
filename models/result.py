from __future__ import annotations

from dataclasses import dataclass, field

from models.state import State
from models.task import TaskID, TaskStatus


@dataclass
class TaskResult:
    task_id: TaskID
    states: list[State]
    status: TaskStatus

    @property
    def ok(self) -> bool:
        return self.status is TaskStatus.DONE


@dataclass
class TestResult:
    passed: bool
    output: str


@dataclass
class WorkflowResult:
    results: list[TaskResult] = field(default_factory=list)
    statuses: list[TaskStatus] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(status is TaskStatus.DONE for status in self.statuses)