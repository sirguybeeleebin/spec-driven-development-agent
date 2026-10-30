from __future__ import annotations

from enum import StrEnum
from typing import NotRequired, TypedDict

from models.llm import Message, Metric
from models.task import Interface, Scenario, TaskID


class AgentRole(StrEnum):
    RESEARCHER = "researcher"
    IMPLEMENTER = "implementer"
    TESTER = "tester"
    FIXER = "fixer"


class AgentStatus(StrEnum):
    DONE = "done"
    FAILED = "failed"


class AgentSession(TypedDict):
    history: list[Message]
    metrics: list[list[Metric]]
    response: str


class State(TypedDict):
    task_id: TaskID
    goal: str
    target: str
    target_test: str
    constitution: str
    interfaces: list[Interface]
    scenarios: list[Scenario]
    activity: NotRequired[str]
    sequence: NotRequired[str]

    researcher: NotRequired[AgentSession]
    implementer: NotRequired[AgentSession]
    tester: NotRequired[AgentSession]
    fixer: NotRequired[AgentSession]

    status: NotRequired[AgentStatus]
    context_map: NotRequired[str]
    scenario: NotRequired[Scenario]
    test_function: NotRequired[str]
    test_source: NotRequired[str]
    test_output: NotRequired[str]