# fsms/workflow.py

from __future__ import annotations

from models import WorkflowStatus


class WorkflowFSM:
    """Per-task state machine inside a workflow.

    IDLE → RUNNING (ancestors already SUCCESS) | HOLD (ancestors pending)
    HOLD → RUNNING (ancestors became SUCCESS) | ERROR (mark_failed)
    RUNNING → SUCCESS (mark_success) | ERROR (mark_error)
    """

    def __init__(self, status: WorkflowStatus = WorkflowStatus.IDLE) -> None:
        self._status: WorkflowStatus = status

    @property
    def status(self) -> WorkflowStatus:
        return self._status

    def mark_hold(self) -> None:
        if self._status is not WorkflowStatus.IDLE:
            raise ValueError(
                f"WorkflowFSM: cannot mark_hold from {self._status.value!r}"
            )
        self._status = WorkflowStatus.HOLD

    def mark_running(self) -> None:
        if self._status not in (
            WorkflowStatus.IDLE,
            WorkflowStatus.HOLD,
        ):
            raise ValueError(
                f"WorkflowFSM: cannot mark_running from {self._status.value!r}"
            )
        self._status = WorkflowStatus.RUNNING

    def mark_success(self) -> None:
        if self._status is not WorkflowStatus.RUNNING:
            raise ValueError(
                f"WorkflowFSM: cannot mark_success from {self._status.value!r}"
            )
        self._status = WorkflowStatus.SUCCESS

    def mark_error(self) -> None:
        if self._status is not WorkflowStatus.RUNNING:
            raise ValueError(
                f"WorkflowFSM: cannot mark_error from {self._status.value!r}"
            )
        self._status = WorkflowStatus.ERROR

    def mark_failed(self) -> None:
        if self._status is not WorkflowStatus.HOLD:
            raise ValueError(
                f"WorkflowFSM: cannot mark_failed from {self._status.value!r}"
            )
        self._status = WorkflowStatus.ERROR
