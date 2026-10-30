# fsms/agent.py

from __future__ import annotations

from models import AgentStatus


class AgentFSM:
    """IDLE → RUNNING → SUCCESS | ERROR."""

    def __init__(self) -> None:
        self._status: AgentStatus = AgentStatus.IDLE

    @property
    def status(self) -> AgentStatus:
        return self._status

    def mark_running(self) -> None:
        if self._status is not AgentStatus.IDLE:
            raise ValueError(
                f"AgentFSM: cannot mark_running from {self._status.value!r}"
            )
        self._status = AgentStatus.RUNNING

    def mark_success(self) -> None:
        if self._status is not AgentStatus.RUNNING:
            raise ValueError(
                f"AgentFSM: cannot mark_success from {self._status.value!r}"
            )
        self._status = AgentStatus.SUCCESS

    def mark_error(self) -> None:
        if self._status is not AgentStatus.RUNNING:
            raise ValueError(f"AgentFSM: cannot mark_error from {self._status.value!r}")
        self._status = AgentStatus.ERROR
