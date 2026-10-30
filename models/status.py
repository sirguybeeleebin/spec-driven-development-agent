# models/statuses.py

from __future__ import annotations

from enum import StrEnum


class AgentStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class TaskStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class WorkflowStatus(StrEnum):
    IDLE = "idle"
    HOLD = "hold"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
