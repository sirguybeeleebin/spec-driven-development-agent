# models/workflow.py

from __future__ import annotations

from dataclasses import dataclass

from models.graph import Graph
from models.status import WorkflowStatus
from models.task import Task, TaskID, TaskResult


@dataclass
class Workflow:
    graph: Graph
    tasks: list[Task]
    statuses: dict[TaskID, WorkflowStatus]


@dataclass
class WorkflowResult:
    results: list[TaskResult]
