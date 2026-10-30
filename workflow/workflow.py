from __future__ import annotations

from models import Task, TaskID, TaskStatus


class Workflow:
    def __init__(
        self,
        tasks: list[Task],
        edges: list[tuple[Task, Task]],
    ) -> None:
        self._tasks = tasks
        self._edges = edges
        self._statuses: dict[TaskID, TaskStatus] = {
            t.task_id: TaskStatus.PENDING for t in tasks
        }

    @property
    def tasks(self) -> list[Task]:
        return list(self._tasks)

    @property
    def edges(self) -> list[tuple[Task, Task]]:
        return list(self._edges)

    def get_ready(self) -> list[Task]:
        ready: list[Task] = []
        for task in self._tasks:
            if self._statuses[task.task_id] is not TaskStatus.PENDING:
                continue
            deps = [src for src, dst in self._edges if dst.task_id == task.task_id]
            if all(self._statuses[d.task_id] is TaskStatus.DONE for d in deps):
                ready.append(task)
        return ready

    def mark_running(self, task: Task) -> None:
        self._statuses[task.task_id] = TaskStatus.RUNNING

    def mark_success(self, task: Task) -> None:
        self._statuses[task.task_id] = TaskStatus.DONE

    def mark_failed(self, task: Task) -> None:
        self._statuses[task.task_id] = TaskStatus.FAILED
