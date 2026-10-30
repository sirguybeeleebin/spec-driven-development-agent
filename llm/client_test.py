# llm/client_test.py

from __future__ import annotations

from openai import OpenAI

from llm.client import LLMClient
from models import Message, MetricName, Role, ToolCall

BASE_URL = "http://192.168.50.236:8080/v1"
API_KEY = "none"
MODEL = "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M"


def _client() -> LLMClient:
    return LLMClient(
        client=OpenAI(base_url=BASE_URL, api_key=API_KEY),
        model=MODEL,
        opts={"temperature": 0.2},
    )


def test_plain_completion_returns_message() -> None:
    client = _client()
    messages = [
        Message(role=Role.USER, content="Reply with exactly: hello"),
    ]
    reply, metrics = client.complete(messages, [])
    assert isinstance(reply, Message)
    assert reply.role is Role.ASSISTANT
    assert isinstance(reply.content, str)
    assert reply.content
    assert reply.tool_calls == []
    names = {m.name for m in metrics}
    assert MetricName.DURATION_SEC in names
    assert MetricName.REQUEST_TOKENS in names
    assert MetricName.RESPONSE_TOKENS in names


def test_usage_metrics_are_positive() -> None:
    client = _client()
    messages = [
        Message(role=Role.USER, content="Say: ok"),
    ]
    _, metrics = client.complete(messages, [])
    by_name = {m.name: m.value for m in metrics}
    assert by_name[MetricName.DURATION_SEC] > 0
    assert by_name[MetricName.REQUEST_TOKENS] > 0
    assert by_name[MetricName.RESPONSE_TOKENS] > 0


def test_tool_call_is_parsed() -> None:
    class EchoTool:
        def get_openai_schema(self) -> dict:
            return {
                "type": "function",
                "function": {
                    "name": "echo",
                    "description": "Echo the given text back.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                        },
                        "required": ["text"],
                    },
                },
            }

        def execute(self, args: dict) -> dict:
            return {"ok": True, "text": args.get("text", "")}

    client = _client()
    messages = [
        Message(
            role=Role.USER,
            content="Call the `echo` tool with text = 'ping'. Do not reply with text.",
        ),
    ]
    reply, _ = client.complete(messages, [EchoTool()])
    assert reply.tool_calls, "expected the model to emit a tool_call"
    call = reply.tool_calls[0]
    assert call.name == "echo"
    assert isinstance(call.arguments, dict)
    assert call.id


def test_assistant_message_with_tool_call_round_trips() -> None:
    client = _client()
    messages = [
        Message(
            role=Role.ASSISTANT,
            content="",
            tool_calls=[
                ToolCall(
                    id="call_test_1",
                    name="echo",
                    arguments={"text": "hi"},
                ),
            ],
        ),
        Message(
            role=Role.TOOL,
            content='{"ok": true, "text": "hi"}',
            tool_call_id="call_test_1",
        ),
        Message(role=Role.USER, content="Reply with exactly: done"),
    ]
    reply, _ = client.complete(messages, [])
    assert reply.role is Role.ASSISTANT
    assert isinstance(reply.content, str)


def test_system_and_user_roles_are_forwarded() -> None:
    client = _client()
    messages = [
        Message(role=Role.SYSTEM, content="You always answer in one word."),
        Message(role=Role.USER, content="What is 2+2?"),
    ]
    reply, _ = client.complete(messages, [])
    assert reply.content
    assert len(reply.content) < 200
