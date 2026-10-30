# runners/workflow.py

from __future__ import annotations

from typing import Protocol

from models import (
    Task,
    TaskResult,
    TaskStatus,
    WorkflowResult,
)


class Workflow(Protocol):
    def get_ready(self) -> list[Task]: ...
    def mark_running(self, task: Task) -> None: ...
    def mark_success(self, task: Task) -> None: ...
    def mark_failed(self, task: Task) -> None: ...


class TaskRunner(Protocol):
    def run(self, task: Task) -> TaskResult: ...


class WorkflowRunner:
    def __init__(self, task_runner: TaskRunner) -> None:
        self._task_runner = task_runner

    def run(self, workflow: Workflow) -> WorkflowResult:
        results: list[TaskResult] = []
        statuses: list[TaskStatus] = []

        while ready := workflow.get_ready():
            for task in ready:
                workflow.mark_running(task)
                try:
                    task_result = self._task_runner.run(task)
                except Exception as exc:
                    print(
                        f"[workflow] task={task.task_id} "
                        f"error={type(exc).__name__}: {exc}",
                        flush=True,
                    )
                    task_result = TaskResult(
                        task_id=task.task_id,
                        results=[],
                        status=TaskStatus.FAILED,
                    )
                results.append(task_result)
                statuses.append(task_result.status)
                if task_result.ok:
                    workflow.mark_success(task)
                else:
                    workflow.mark_failed(task)

        return WorkflowResult(results=results, statuses=statuses)
