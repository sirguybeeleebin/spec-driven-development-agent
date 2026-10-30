# llm/client_test.py

from __future__ import annotations

from openai import OpenAI

from llm import LLMClient
from models import (
    Message,
    MetricName,
    Role,
    ToolCall,
)

BASE_URL = "http://192.168.50.236:8080/v1"
API_KEY = "none"
MODEL = "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M"


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
                        "text": {
                            "type": "string",
                            "description": "Text to echo.",
                        },
                    },
                    "required": ["text"],
                },
            },
        }

    def execute(self, args: dict) -> dict:
        return {"echoed": args["text"]}


def _llm() -> LLMClient:
    return LLMClient(
        client=OpenAI(base_url=BASE_URL, api_key=API_KEY),
        model=MODEL,
        opts={"temperature": 0.0},
    )


def _system(content: str) -> Message:
    return Message(role=Role.SYSTEM, content=content)


def _user(content: str) -> Message:
    return Message(role=Role.USER, content=content)


def _assistant(content: str) -> Message:
    return Message(role=Role.ASSISTANT, content=content)


def _tool(content: str, tool_call_id: str) -> Message:
    return Message(
        role=Role.TOOL,
        content=content,
        tool_call_id=tool_call_id,
    )


def llm_returns_assistant_text_test() -> None:
    print(f"[{__name__}] llm_returns_assistant_text_test")
    llm = _llm()
    messages = [_user("Reply with exactly one word: pong")]
    reply, metrics = llm.complete(messages, [])
    assert reply.role is Role.ASSISTANT
    assert reply.tool_calls == []
    assert reply.content.strip()
    assert metrics


def llm_returns_duration_metric_test() -> None:
    print(f"[{__name__}] llm_returns_duration_metric_test")
    llm = _llm()
    messages = [_user("Say 'ok'.")]
    _, metrics = llm.complete(messages, [])
    names = {m.name for m in metrics}
    assert MetricName.DURATION_SEC in names
    duration = next(m.value for m in metrics if m.name is MetricName.DURATION_SEC)
    assert duration >= 0.0


def llm_returns_usage_metrics_test() -> None:
    print(f"[{__name__}] llm_returns_usage_metrics_test")
    llm = _llm()
    messages = [_user("Say 'ok'.")]
    _, metrics = llm.complete(messages, [])
    names = {m.name for m in metrics}
    if MetricName.REQUEST_TOKENS not in names:
        return
    assert MetricName.RESPONSE_TOKENS in names
    request = next(m.value for m in metrics if m.name is MetricName.REQUEST_TOKENS)
    response = next(m.value for m in metrics if m.name is MetricName.RESPONSE_TOKENS)
    assert request > 0
    assert response > 0


def llm_handles_multi_turn_test() -> None:
    print(f"[{__name__}] llm_handles_multi_turn_test")
    llm = _llm()
    messages = [
        _system("You are a helpful assistant."),
        _user("My name is Sergey."),
        _assistant("Nice to meet you, Sergey."),
        _user("What is my name?"),
    ]
    reply, _ = llm.complete(messages, [])
    assert reply.role is Role.ASSISTANT
    assert "Sergey" in reply.content


def llm_calls_native_tool_test() -> None:
    print(f"[{__name__}] llm_calls_native_tool_test")
    llm = _llm()
    echo = EchoTool()
    messages = [_user("Call the echo tool with the text 'hello'.")]
    reply, _ = llm.complete(messages, [echo])
    assert reply.role is Role.ASSISTANT
    assert reply.tool_calls, (
        f"model did not use the provided tool; reply.content={reply.content!r}"
    )
    tc = reply.tool_calls[0]
    assert tc.name == "echo"
    assert tc.id
    assert tc.arguments.get("text") == "hello"


def llm_handles_tool_message_test() -> None:
    print(f"[{__name__}] llm_handles_tool_message_test")
    llm = _llm()
    echo = EchoTool()
    messages = [
        _user("Echo the word 'hello' using the echo tool."),
        Message(
            role=Role.ASSISTANT,
            content="",
            tool_calls=[
                ToolCall(
                    id="call_test_1",
                    name="echo",
                    arguments={"text": "hello"},
                ),
            ],
        ),
        _tool('{"echoed": "hello"}', "call_test_1"),
    ]
    reply, _ = llm.complete(messages, [echo])
    assert reply.role is Role.ASSISTANT
    assert reply.content or reply.tool_calls


def llm_arguments_are_dict_test() -> None:
    print(f"[{__name__}] llm_arguments_are_dict_test")
    llm = _llm()
    echo = EchoTool()
    messages = [_user("Call the echo tool with the text 'hello'.")]
    reply, _ = llm.complete(messages, [echo])
    assert reply.tool_calls
    tc = reply.tool_calls[0]
    assert isinstance(tc.arguments, dict)
    assert "text" in tc.arguments
