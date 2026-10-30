# llm/client.py

from __future__ import annotations

import json
import time
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
            **self._opts,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if openai_tools:
            kwargs["tools"] = openai_tools

        print(
            f"[llm] complete model={self._model} "
            f"messages={len(messages)} tools={len(tools)}",
            flush=True,
        )
        print("[llm] stream start", flush=True)

        started = time.perf_counter()
        stream = self._client.chat.completions.create(**kwargs)

        content_parts: list[str] = []
        tool_calls_acc: dict[int, dict[str, str]] = {}
        announced: set[int] = set()
        usage = None
        text_emitted = False
        args_emitted = False
        chunks = 0

        for chunk in stream:
            chunks += 1

            if getattr(chunk, "usage", None) is not None:
                usage = chunk.usage
            if not getattr(chunk, "choices", None):
                continue

            delta = chunk.choices[0].delta

            content_delta = getattr(delta, "content", None)
            if content_delta:
                if args_emitted:
                    print(flush=True)
                    args_emitted = False
                content_parts.append(content_delta)
                print(content_delta, end="", flush=True)
                text_emitted = True

            tool_calls_delta = getattr(delta, "tool_calls", None)
            if tool_calls_delta:
                for tc in tool_calls_delta:
                    entry = tool_calls_acc.setdefault(
                        tc.index,
                        {"id": "", "name": "", "arguments": ""},
                    )
                    if tc.id:
                        entry["id"] = tc.id
                    fn = getattr(tc, "function", None)
                    if fn is None:
                        continue
                    if fn.name:
                        entry["name"] += fn.name
                        if tc.index not in announced:
                            announced.add(tc.index)
                            if text_emitted:
                                print(flush=True)
                                text_emitted = False
                            print(
                                f"\n[llm] tool_call id={entry['id']} name=",
                                end="",
                                flush=True,
                            )
                        print(fn.name, end="", flush=True)
                    if fn.arguments:
                        if not args_emitted:
                            if text_emitted:
                                print(flush=True)
                                text_emitted = False
                            print(" args=", end="", flush=True)
                            args_emitted = True
                        entry["arguments"] += fn.arguments
                        print(fn.arguments, end="", flush=True)

        if text_emitted or args_emitted:
            print(flush=True)

        duration = time.perf_counter() - started
        content = "".join(content_parts)

        tool_calls: list[ToolCall] = [
            ToolCall(
                id=entry["id"],
                name=entry["name"],
                arguments=json.loads(entry["arguments"] or "{}"),
            )
            for _, entry in sorted(tool_calls_acc.items())
        ]

        metrics: list[Metric] = [
            Metric(name=MetricName.DURATION_SEC, value=float(duration)),
        ]
        request_tokens: int | None = None
        response_tokens: int | None = None
        if usage is not None:
            request_tokens = int(usage.prompt_tokens or 0)
            response_tokens = int(usage.completion_tokens or 0)
            metrics.append(
                Metric(
                    name=MetricName.REQUEST_TOKENS,
                    value=float(request_tokens),
                )
            )
            metrics.append(
                Metric(
                    name=MetricName.RESPONSE_TOKENS,
                    value=float(response_tokens),
                )
            )

        if tool_calls:
            names = ", ".join(tc.name for tc in tool_calls)
            print(
                f"[llm] tool_calls={len(tool_calls)} names=[{names}]",
                flush=True,
            )
        print(
            f"[llm] response duration_sec={duration:.3f} chunks={chunks} "
            f"request_tokens="
            f"{request_tokens if request_tokens is not None else '—'} "
            f"response_tokens="
            f"{response_tokens if response_tokens is not None else '—'}",
            flush=True,
        )

        return (
            Message(
                role=Role.ASSISTANT,
                content=content if content else "",
                tool_calls=tool_calls,
            ),
            metrics,
        )
