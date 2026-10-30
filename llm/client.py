# llm/client.py

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any, Protocol

from openai import OpenAI

from models import (
    Message,
    Metric,
    MetricName,
    Role,
    ToolCall,
)


class Tool(Protocol):
    def get_openai_schema(self) -> dict: ...
    def execute(self, args: dict) -> dict: ...


class LLMClient:
    def __init__(
        self,
        client: OpenAI,
        model: str,
        opts: dict[str, Any],
    ) -> None:
        self._client = client
        self._model = model
        self._opts: dict[str, Any] = dict(opts)

    def complete(
        self,
        messages: list[Message],
        tools: list[Tool],
    ) -> tuple[Message, list[Metric]]:
        openai_messages: list[dict] = []
        for m in messages:
            if m.role is Role.TOOL:
                openai_messages.append(
                    {
                        "role": "tool",
                        "content": m.content,
                        "tool_call_id": m.tool_call_id,
                    }
                )
            elif m.tool_calls:
                openai_messages.append(
                    {
                        "role": "assistant",
                        "content": m.content or None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                            for tc in m.tool_calls
                        ],
                    }
                )
            else:
                openai_messages.append(
                    {
                        "role": str(m.role),
                        "content": m.content,
                    }
                )

        openai_tools = [t.get_openai_schema() for t in tools]

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": openai_messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            **self._opts,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools

        started = time.perf_counter()
        stream = self._client.chat.completions.create(**kwargs)

        content_parts: list[str] = []
        streamed_tool_calls: dict[int, dict[str, str]] = {}
        printed_content_header = False
        printing_tool_index: int | None = None
        usage = None

        for chunk in stream:
            if chunk.usage is not None:
                usage = chunk.usage
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            if delta is None:
                continue

            if delta.content:
                if printed_content_header is False:
                    print("[llm] content:", flush=True)
                    printed_content_header = True
                print(delta.content, end="", flush=True)
                content_parts.append(delta.content)

            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    entry = streamed_tool_calls.setdefault(
                        tc_delta.index,
                        {"id": "", "name": "", "arguments": ""},
                    )
                    if tc_delta.id:
                        entry["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            entry["name"] = tc_delta.function.name
                            print(
                                f"\n[llm] tool_call start: {tc_delta.function.name}",
                                flush=True,
                            )
                            printing_tool_index = tc_delta.index
                        if tc_delta.function.arguments:
                            if printing_tool_index != tc_delta.index:
                                print(
                                    f"\n[llm] tool_call start: {entry['name'] or '?'}",
                                    flush=True,
                                )
                                printing_tool_index = tc_delta.index
                            print(
                                tc_delta.function.arguments,
                                end="",
                                flush=True,
                            )
                            entry["arguments"] += tc_delta.function.arguments

        duration = time.perf_counter() - started

        if printed_content_header:
            print(flush=True)
        if printing_tool_index is not None:
            print(flush=True)

        content = "".join(content_parts)

        tool_calls: list[ToolCall] = []
        for idx in sorted(streamed_tool_calls.keys()):
            entry = streamed_tool_calls[idx]
            try:
                arguments = json.loads(entry["arguments"] or "{}")
            except (json.JSONDecodeError, TypeError):
                arguments = {}
            tool_calls.append(
                ToolCall(
                    id=entry["id"] or f"stream_{uuid.uuid4().hex[:24]}",
                    name=entry["name"],
                    arguments=arguments,
                )
            )

        if not tool_calls and content:
            for match in re.finditer(
                r"<function=(\w+)>(.*?)</function>",
                content,
                re.DOTALL,
            ):
                arguments: dict[str, Any] = {}
                for param in re.finditer(
                    r"<parameter=(\w+)>\s*(.*?)\s*</parameter>",
                    match.group(2),
                    re.DOTALL,
                ):
                    raw = param.group(2)
                    try:
                        arguments[param.group(1)] = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        arguments[param.group(1)] = raw
                tool_calls.append(
                    ToolCall(
                        id=f"xml_{uuid.uuid4().hex[:24]}",
                        name=match.group(1),
                        arguments=arguments,
                    )
                )
            if tool_calls:
                content = re.sub(
                    r"<function=\w+>.*?</function>",
                    "",
                    content,
                    flags=re.DOTALL,
                ).strip()

        for tc in tool_calls:
            print(
                f"[llm] tool_call: {tc.name} "
                f"args={json.dumps(tc.arguments, ensure_ascii=True)}",
                flush=True,
            )

        reply = Message(
            role=Role.ASSISTANT,
            content=content,
            tool_calls=tool_calls,
        )

        metrics: list[Metric] = [
            Metric(name=MetricName.DURATION_SEC, value=float(duration)),
        ]
        if usage is not None:
            metrics.append(
                Metric(
                    name=MetricName.REQUEST_TOKENS,
                    value=float(int(usage.prompt_tokens or 0)),
                )
            )
            metrics.append(
                Metric(
                    name=MetricName.RESPONSE_TOKENS,
                    value=float(int(usage.completion_tokens or 0)),
                )
            )

        return reply, metrics
