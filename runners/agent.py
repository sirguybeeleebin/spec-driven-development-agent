# runners/agent.py

from __future__ import annotations

import json
from typing import Protocol

from models import (
    AgentResult,
    AgentStatus,
    Message,
    Metric,
    Role,
    Skill,
    State,
    ToolCall,
)


class Tool(Protocol):
    def get_openai_schema(self) -> dict: ...
    def execute(self, args: dict) -> dict: ...


class LLMClient(Protocol):
    def complete(
        self,
        messages: list[Message],
        tools: list[Tool],
    ) -> tuple[Message, list[Metric]]: ...


class PromptProvider(Protocol):
    def format_system(self, skills: list[Skill]) -> str: ...
    def format_user(self, state: State) -> str: ...
    @property
    def final_user(self) -> str: ...


class Hook(Protocol):
    def after_tool_call(
        self,
        *,
        state: State,
        tool_call: ToolCall,
        result: dict,
    ) -> dict: ...


class AgentFSM(Protocol):
    @property
    def status(self) -> AgentStatus: ...
    def mark_running(self) -> None: ...
    def mark_success(self) -> None: ...
    def mark_error(self) -> None: ...


class AgentRunner:
    def __init__(
        self,
        *,
        llm: LLMClient,
        prompt_provider: PromptProvider,
        skills: list[Skill],
        tools: list[Tool],
        hooks: list[Hook] | None = None,
        max_iterations: int,
        fsm: AgentFSM,
    ) -> None:
        self._llm = llm
        self._prompt_provider = prompt_provider
        self._skills = skills
        self._tools = tools
        self._tools_by_name = {
            t.get_openai_schema()["function"]["name"]: t for t in tools
        }
        self._hooks = list(hooks or [])
        self._max_iterations = max_iterations
        self._fsm = fsm

    def run(self, *, state: State) -> AgentResult:
        self._fsm.mark_running()

        session: list[Message] = []
        metrics: list[list[Metric]] = []

        try:
            system_content = self._prompt_provider.format_system(self._skills)
            user_content = self._prompt_provider.format_user(state)

            session.append(Message(role=Role.USER, content=user_content))

            for _ in range(self._max_iterations):
                messages = [
                    Message(role=Role.SYSTEM, content=system_content),
                    *session,
                ]

                reply, reply_metrics = self._llm.complete(messages, self._tools)
                session.append(reply)
                metrics.append(reply_metrics)

                if not reply.tool_calls:
                    self._fsm.mark_success()
                    return AgentResult(
                        status=self._fsm.status,
                        response=reply.content or "",
                        messages=session,
                        metrics=metrics,
                    )

                for tool_call in reply.tool_calls:
                    result = self._tools_by_name[tool_call.name].execute(
                        tool_call.arguments
                    )

                    for hook in self._hooks:
                        result = hook.after_tool_call(
                            state=state,
                            tool_call=tool_call,
                            result=result,
                        )

                    session.append(
                        Message(
                            role=Role.TOOL,
                            content=json.dumps(result, ensure_ascii=False, default=str),
                            tool_call_id=tool_call.id,
                        )
                    )

            session.append(
                Message(
                    role=Role.USER,
                    content=self._prompt_provider.final_user,
                )
            )
            final_messages = [
                Message(role=Role.SYSTEM, content=system_content),
                *session,
            ]
            reply, reply_metrics = self._llm.complete(final_messages, [])
            session.append(reply)
            metrics.append(reply_metrics)

            self._fsm.mark_success()
            return AgentResult(
                status=self._fsm.status,
                response=reply.content or "",
                messages=session,
                metrics=metrics,
            )
        except Exception as exc:
            self._fsm.mark_error()
            return AgentResult(
                status=self._fsm.status,
                response=f"{type(exc).__name__}: {exc}",
                messages=session,
                metrics=metrics,
            )
