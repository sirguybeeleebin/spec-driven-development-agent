from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MetricName(StrEnum):
    DURATION_SEC = "duration_sec"
    REQUEST_TOKENS = "request_tokens"
    RESPONSE_TOKENS = "response_tokens"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Message:
    role: Role
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None


@dataclass
class Metric:
    name: MetricName
    value: float
