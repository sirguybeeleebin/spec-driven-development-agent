from __future__ import annotations

import json
from typing import Any, Protocol

from hooks import StopError
from models import (
    AgentStatus,
    AgentRole,
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


class PreHook(Protocol):
    def __call__(
        self,
        *,
        state: State,
        role: AgentRole,
        tool_call: ToolCall,
        args: dict[str, Any],
    ) -> str | None: ...


class PostHook(Protocol):
    def __call__(
        self,
        *,
        state: State,
        role: AgentRole,
        tool_call: ToolCall,
        args: dict[str, Any],
        result: dict,
    ) -> None: ...


class PromptProvider(Protocol):
    @property
    def role(self) -> AgentRole: ...

    def format_system(self, skills: list[Skill]) -> str: ...

    @property
    def summary_request(self) -> str: ...

    def format_user(self, state: State) -> str: ...


class Agent:
    def __init__(
        self,
        *,
        llm: LLMClient,
        prompt_provider: PromptProvider,
        skills: list[Skill],
        tools: list[Tool],
        pre_hooks: list[PreHook],
        post_hooks: list[PostHook],
        max_iterations: int,
    ) -> None:
        self._llm = llm
        self._prompt_provider = prompt_provider
        self._skills = skills
        self._tools = list(tools)
        self._tools_by_name = {
            t.get_openai_schema()["function"]["name"]: t for t in self._tools
        }
        self._pre_hooks = pre_hooks
        self._post_hooks = post_hooks
        self._max_iterations = max_iterations

    def run(self, state: State) -> State:
        role = self._prompt_provider.role

        next_state: State = state.copy()
        next_state[role] = {
            "history": [],
            "metrics": [],
            "response": "",
        }
        next_state["status"] = AgentStatus.FAILED

        session = next_state[role]

        system_content = self._prompt_provider.format_system(self._skills)
        tool_names = [
            t.get_openai_schema()["function"]["name"] for t in self._tools
        ]

        print(
            f"[agent.{role}] start "
            f"system_len={len(system_content)} "
            f"tools={tool_names} "
            f"pre_hooks={[type(h).__name__ for h in self._pre_hooks]} "
            f"post_hooks={[type(h).__name__ for h in self._post_hooks]} "
            f"max_iterations={self._max_iterations}"
        )

        for iteration in range(self._max_iterations):
            user_content = self._prompt_provider.format_user(next_state)

            messages: list[Message] = [
                Message(role=Role.SYSTEM, content=system_content),
                Message(role=Role.USER, content=user_content),
            ]

            print(
                f"[agent.{role}] iter={iteration + 1}/{self._max_iterations} "
                f"messages={len(messages)} "
                f"user_len={len(user_content)} "
                f"history={len(session['history'])}"
            )

            reply, metrics = self._llm.complete(messages, self._tools)
            session["history"].append(reply)
            session["metrics"].append(metrics)

            tool_call_names = [tc.name for tc in (reply.tool_calls or [])]
            print(
                f"[agent.{role}] iter={iteration + 1} "
                f"reply_len={len(reply.content or '')} "
                f"tool_calls={tool_call_names}"
            )

            if not reply.tool_calls:
                session["response"] = reply.content or ""
                next_state["status"] = AgentStatus.DONE
                print(
                    f"[agent.{role}] done after {iteration + 1} iteration(s) "
                    f"history={len(session['history'])} "
                    f"final_len={len(session['response'])}"
                )
                return next_state

            for tc in reply.tool_calls:
                args = dict(tc.arguments)

                hint: str | None = None
                for pre in self._pre_hooks:
                    hint = pre(
                        state=next_state,
                        role=role,
                        tool_call=tc,
                        args=args,
                    )
                    if hint is not None:
                        print(
                            f"[agent.{role}] pre_hook={type(pre).__name__} "
                            f"blocked tool={tc.name}"
                        )
                        break

                if hint is not None:
                    result: dict = {"hint": hint}
                    print(f"[agent.{role}] tool={tc.name} hint={hint!r}")
                else:
                    tool = self._tools_by_name.get(tc.name)
                    if tool is None:
                        result = {"error": f"unknown tool: {tc.name}"}
                        print(f"[agent.{role}] tool={tc.name} UNKNOWN")
                    else:
                        try:
                            result = tool.execute(args)
                            result_json = json.dumps(result, ensure_ascii=True)
                            print(
                                f"[agent.{role}] tool={tc.name} ok "
                                f"result_len={len(result_json)}"
                            )
                        except Exception as exc:
                            result = {
                                "error": f"{type(exc).__name__}: {exc}"
                            }
                            print(
                                f"[agent.{role}] tool={tc.name} EXC "
                                f"{type(exc).__name__}: {exc}"
                            )

                        try:
                            for post in self._post_hooks:
                                post(
                                    state=next_state,
                                    role=role,
                                    tool_call=tc,
                                    args=args,
                                    result=result,
                                )
                        except StopError:
                            print(
                                f"[agent.{role}] STOP after tool={tc.name}"
                            )
                            session["history"].append(
                                Message(
                                    role=Role.TOOL,
                                    content=json.dumps(
                                        result, ensure_ascii=True
                                    ),
                                    tool_call_id=tc.id,
                                )
                            )
                            final_user_content = (
                                self._prompt_provider.format_user(next_state)
                                + self._prompt_provider.summary_request
                            )
                            final_messages: list[Message] = [
                                Message(
                                    role=Role.SYSTEM,
                                    content=system_content,
                                ),
                                Message(
                                    role=Role.USER,
                                    content=final_user_content,
                                ),
                            ]
                            final_reply, final_metrics = self._llm.complete(
                                final_messages, []
                            )
                            session["history"].append(final_reply)
                            session["metrics"].append(final_metrics)
                            session["response"] = final_reply.content or ""
                            next_state["status"] = AgentStatus.DONE
                            print(
                                f"[agent.{role}] stop-final "
                                f"messages={len(final_messages)} "
                                f"user_len={len(final_user_content)} "
                                f"reply_len={len(session['response'])}"
                            )
                            return next_state

                session["history"].append(
                    Message(
                        role=Role.TOOL,
                        content=json.dumps(result, ensure_ascii=True),
                        tool_call_id=tc.id,
                    )
                )

        print(
            f"[agent.{role}] FAILED after {self._max_iterations} iteration(s) "
            f"history={len(session['history'])}"
        )
        return next_state