# models/agent.py

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from models.llm import Message, Metric
from models.status import AgentStatus


class Agents(StrEnum):
    RESEARCHER = "researcher"
    IMPLEMENTER = "implementer"
    TESTER = "tester"
    FIXER = "fixer"


@dataclass
class AgentResult:
    status: AgentStatus
    response: str
    messages: list[Message]
    metrics: list[list[Metric]]
