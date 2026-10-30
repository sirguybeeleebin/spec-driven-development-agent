# fsms/task.py

from __future__ import annotations

from models import TaskStatus


class TaskFSM:
    """IDLE → RUNNING → SUCCESS | ERROR."""

    def __init__(self) -> None:
        self._status: TaskStatus = TaskStatus.IDLE

    @property
    def status(self) -> TaskStatus:
        return self._status

    def mark_running(self) -> None:
        if self._status is not TaskStatus.IDLE:
            raise ValueError(
                f"TaskFSM: cannot mark_running from {self._status.value!r}"
            )
        self._status = TaskStatus.RUNNING

    def mark_success(self) -> None:
        if self._status is not TaskStatus.RUNNING:
            raise ValueError(
                f"TaskFSM: cannot mark_success from {self._status.value!r}"
            )
        self._status = TaskStatus.SUCCESS

    def mark_error(self) -> None:
        if self._status is not TaskStatus.RUNNING:
            raise ValueError(f"TaskFSM: cannot mark_error from {self._status.value!r}")
        self._status = TaskStatus.ERROR
