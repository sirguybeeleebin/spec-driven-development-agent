# runners/workflow.py

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from models import (
    Task,
    TaskResult,
    TaskStatus,
    Workflow,
    WorkflowResult,
    WorkflowStatus,
)


class TaskRunner(Protocol):
    def run(self, task: Task) -> TaskResult: ...


class WorkflowFSM(Protocol):
    @property
    def status(self) -> WorkflowStatus: ...
    def mark_hold(self) -> None: ...
    def mark_running(self) -> None: ...
    def mark_success(self) -> None: ...
    def mark_error(self) -> None: ...
    def mark_failed(self) -> None: ...


class Scheduler(Protocol):
    def get_ready_tasks(self, workflow: Workflow) -> list[Task]: ...


class WorkflowRunner:
    def __init__(
        self,
        *,
        task_runner: TaskRunner,
        scheduler: Scheduler,
        fsm_factory: Callable[[WorkflowStatus], WorkflowFSM],
    ) -> None:
        self._task_runner = task_runner
        self._scheduler = scheduler
        self._fsm_factory = fsm_factory

    def run(self, workflow: Workflow) -> WorkflowResult:
        results: list[TaskResult] = []

        while True:
            ready = self._scheduler.get_ready_tasks(workflow)
            if not ready:
                for task in workflow.tasks:
                    if workflow.statuses[task.task_id] is WorkflowStatus.HOLD:
                        fsm = self._fsm_factory(workflow.statuses[task.task_id])
                        fsm.mark_failed()
                        workflow.statuses[task.task_id] = fsm.status
                        results.append(
                            TaskResult(
                                task_id=task.task_id,
                                status=TaskStatus.ERROR,
                                results=[],
                            )
                        )
                break

            for task in ready:
                fsm = self._fsm_factory(workflow.statuses[task.task_id])
                fsm.mark_running()
                workflow.statuses[task.task_id] = fsm.status

                result = self._task_runner.run(task)
                results.append(result)

                fsm = self._fsm_factory(workflow.statuses[task.task_id])
                if result.status is TaskStatus.SUCCESS:
                    fsm.mark_success()
                else:
                    fsm.mark_error()
                workflow.statuses[task.task_id] = fsm.status

        return WorkflowResult(results=results)
