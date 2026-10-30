# runners/agent_test.py

from __future__ import annotations

from models import (
    AgentStatus,
    Message,
    Metric,
    MetricName,
    Role,
    Skill,
    State,
    ToolCall,
)
from runners.agent import AgentRunner

# ---------- stubs ----------


class FakeAgentFSM:
    def __init__(self) -> None:
        self._status = AgentStatus.IDLE
        self.transitions: list[str] = []

    @property
    def status(self) -> AgentStatus:
        return self._status

    def mark_running(self) -> None:
        self.transitions.append("running")
        self._status = AgentStatus.RUNNING

    def mark_success(self) -> None:
        self.transitions.append("success")
        self._status = AgentStatus.SUCCESS

    def mark_error(self) -> None:
        self.transitions.append("error")
        self._status = AgentStatus.ERROR


class FakeLLM:
    def __init__(self, replies: list[Message]) -> None:
        self._replies = list(replies)
        self.calls: list[tuple[list[Message], list]] = []

    def complete(
        self,
        messages: list[Message],
        tools: list,
    ) -> tuple[Message, list[Metric]]:
        self.calls.append((list(messages), list(tools)))
        reply = self._replies.pop(0)
        metrics = [Metric(name=MetricName.DURATION_SEC, value=1.0)]
        return reply, metrics


class BoomLLM:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.calls: list[tuple[list[Message], list]] = []

    def complete(
        self,
        messages: list[Message],
        tools: list,
    ) -> tuple[Message, list[Metric]]:
        self.calls.append((list(messages), list(tools)))
        raise self._exc


class FakePromptProvider:
    def __init__(
        self,
        system: str = "SYSTEM",
        user: str = "USER",
        final: str = "FINAL",
    ) -> None:
        self._system = system
        self._user = user
        self._final = final
        self.system_calls: list[list[Skill]] = []
        self.user_calls: list[State] = []

    def format_system(self, skills: list[Skill]) -> str:
        self.system_calls.append(list(skills))
        return self._system

    def format_user(self, state: State) -> str:
        self.user_calls.append(state)
        return self._user

    @property
    def final_user(self) -> str:
        return self._final


class BoomPromptProvider(FakePromptProvider):
    def __init__(self, exc: Exception) -> None:
        super().__init__()
        self._exc = exc

    def format_system(self, skills: list[Skill]) -> str:
        raise self._exc


class FakeTool:
    def __init__(self, name: str, result: dict | None = None) -> None:
        self._name = name
        self._result = result if result is not None else {"ok": True}
        self.calls: list[dict] = []

    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {"name": self._name, "parameters": {}},
        }

    def execute(self, args: dict) -> dict:
        self.calls.append(args)
        return self._result


class BoomTool(FakeTool):
    def __init__(self, name: str, exc: Exception) -> None:
        super().__init__(name)
        self._exc = exc

    def execute(self, args: dict) -> dict:
        self.calls.append(args)
        raise self._exc


class BoomHook:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def after_tool_call(self, *, state, tool_call, result):
        raise self._exc


# ---------- helpers ----------


def _final_reply(content: str = "done") -> Message:
    return Message(role=Role.ASSISTANT, content=content)


def _tool_reply(
    name: str,
    args: dict,
    call_id: str = "call_1",
    content: str = "",
) -> Message:
    return Message(
        role=Role.ASSISTANT,
        content=content,
        tool_calls=[ToolCall(id=call_id, name=name, arguments=args)],
    )


def _tool_reply_multi(
    calls: list[tuple[str, str, dict]],
    content: str = "",
) -> Message:
    return Message(
        role=Role.ASSISTANT,
        content=content,
        tool_calls=[
            ToolCall(id=cid, name=name, arguments=args) for name, cid, args in calls
        ],
    )


def _make_runner(
    llm,
    provider=None,
    skills=None,
    tools=None,
    hooks=None,
    max_iterations=5,
    fsm=None,
) -> AgentRunner:
    return AgentRunner(
        llm=llm,
        prompt_provider=provider or FakePromptProvider(),
        skills=skills or [],
        tools=tools or [],
        hooks=hooks,
        max_iterations=max_iterations,
        fsm=fsm or FakeAgentFSM(),
    )


# ---------- init ----------


def test_init_builds_tools_by_name_from_schema() -> None:
    alpha = FakeTool("alpha")
    beta = FakeTool("beta")
    runner = _make_runner(FakeLLM([]), tools=[alpha, beta])
    assert runner._tools_by_name == {"alpha": alpha, "beta": beta}


# ---------- run: happy path (no tool calls) ----------


def test_run_returns_success_on_final_reply() -> None:
    llm = FakeLLM([_final_reply("hello")])
    runner = _make_runner(llm)
    result = runner.run(state=State(target_file="x.py"))

    assert result.status is AgentStatus.SUCCESS
    assert result.response == "hello"


def test_run_returns_empty_string_when_final_content_is_none() -> None:
    reply = Message(role=Role.ASSISTANT, content=None)
    llm = FakeLLM([reply])
    runner = _make_runner(llm)
    result = runner.run(state=State())
    assert result.response == ""


def test_run_calls_prompt_provider_with_state_and_skills() -> None:
    skills = [Skill(name="s", description="d", content="c")]
    state = State(goal="g", target_file="x.py")
    provider = FakePromptProvider()
    runner = _make_runner(FakeLLM([_final_reply()]), provider=provider, skills=skills)

    runner.run(state=state)

    assert provider.system_calls == [skills]
    assert provider.user_calls == [state]


def test_run_only_calls_llm_once_when_no_tool_calls() -> None:
    llm = FakeLLM([_final_reply()])
    runner = _make_runner(llm)
    runner.run(state=State())
    assert len(llm.calls) == 1


def test_run_system_message_precedes_session() -> None:
    llm = FakeLLM([_final_reply()])
    provider = FakePromptProvider(system="SYS", user="USR")
    runner = _make_runner(llm, provider=provider)
    runner.run(state=State())

    messages, _ = llm.calls[0]
    assert messages[0].role is Role.SYSTEM
    assert messages[0].content == "SYS"
    assert messages[1].role is Role.USER
    assert messages[1].content == "USR"


def test_run_session_includes_assistant_reply() -> None:
    llm = FakeLLM([_final_reply("hi")])
    runner = _make_runner(llm)
    result = runner.run(state=State())

    roles = [m.role for m in result.messages]
    assert roles == [Role.USER, Role.ASSISTANT]
    assert result.messages[-1].content == "hi"


def test_run_collects_one_metrics_entry_per_llm_call() -> None:
    llm = FakeLLM([_final_reply()])
    runner = _make_runner(llm)
    result = runner.run(state=State())

    assert len(result.metrics) == 1
    assert result.metrics[0][0].name is MetricName.DURATION_SEC


# ---------- run: single tool call ----------


def test_run_executes_tool_and_appends_tool_message() -> None:
    tool = FakeTool("append", result={"ok": True, "path": "x"})
    llm = FakeLLM(
        [
            _tool_reply("append", {"path": "x", "content": "y"}, call_id="c1"),
            _final_reply("done"),
        ]
    )
    runner = _make_runner(llm, tools=[tool])

    result = runner.run(state=State())

    assert result.status is AgentStatus.SUCCESS
    assert tool.calls == [{"path": "x", "content": "y"}]
    roles = [m.role for m in result.messages]
    assert roles == [
        Role.USER,
        Role.ASSISTANT,
        Role.TOOL,
        Role.ASSISTANT,
    ]


def test_run_tool_message_carries_call_id_and_serialized_result() -> None:
    tool = FakeTool("t", result={"ok": True, "value": 42})
    llm = FakeLLM(
        [
            _tool_reply("t", {"a": 1}, call_id="xyz"),
            _final_reply(),
        ]
    )
    runner = _make_runner(llm, tools=[tool])

    result = runner.run(state=State())
    tool_msg = result.messages[2]

    assert tool_msg.role is Role.TOOL
    assert tool_msg.tool_call_id == "xyz"
    assert '"ok": true' in tool_msg.content
    assert '"value": 42' in tool_msg.content


def test_run_passes_tools_to_every_llm_call_until_final() -> None:
    tool = FakeTool("t")
    llm = FakeLLM([_tool_reply("t", {}), _final_reply()])
    runner = _make_runner(llm, tools=[tool])
    runner.run(state=State())

    assert llm.calls[0][1] == [tool]
    assert llm.calls[1][1] == [tool]


# ---------- run: multiple tool calls in one reply ----------


def test_run_executes_all_tool_calls_in_order() -> None:
    a = FakeTool("a", result={"ok": True})
    b = FakeTool("b", result={"ok": True})
    llm = FakeLLM(
        [
            _tool_reply_multi(
                [
                    ("a", "c1", {"x": 1}),
                    ("b", "c2", {"y": 2}),
                ]
            ),
            _final_reply(),
        ]
    )
    runner = _make_runner(llm, tools=[a, b])

    result = runner.run(state=State())

    assert a.calls == [{"x": 1}]
    assert b.calls == [{"y": 2}]
    roles = [m.role for m in result.messages]
    assert roles == [
        Role.USER,
        Role.ASSISTANT,
        Role.TOOL,
        Role.TOOL,
        Role.ASSISTANT,
    ]
    assert result.messages[2].tool_call_id == "c1"
    assert result.messages[3].tool_call_id == "c2"


# ---------- run: exceptions become ERROR results ----------


def test_run_returns_error_on_tool_exception() -> None:
    tool = BoomTool("boom", ValueError("boom"))
    llm = FakeLLM([_tool_reply("boom", {})])
    runner = _make_runner(llm, tools=[tool])

    result = runner.run(state=State())

    assert result.status is AgentStatus.ERROR
    assert "ValueError" in result.response
    assert "boom" in result.response
    assert [m.role for m in result.messages] == [Role.USER, Role.ASSISTANT]
    assert len(result.metrics) == 1


def test_run_returns_error_on_unknown_tool_name() -> None:
    llm = FakeLLM([_tool_reply("ghost", {})])
    runner = _make_runner(llm, tools=[])

    result = runner.run(state=State())

    assert result.status is AgentStatus.ERROR
    assert "KeyError" in result.response
    assert "ghost" in result.response
    assert [m.role for m in result.messages] == [Role.USER, Role.ASSISTANT]
    assert len(result.metrics) == 1


def test_run_returns_error_on_hook_exception() -> None:
    tool = FakeTool("t")
    llm = FakeLLM([_tool_reply("t", {})])
    runner = _make_runner(
        llm, tools=[tool], hooks=[BoomHook(RuntimeError("hook exploded"))]
    )

    result = runner.run(state=State())

    assert result.status is AgentStatus.ERROR
    assert "RuntimeError" in result.response
    assert "hook exploded" in result.response
    assert tool.calls == [{}]
    assert [m.role for m in result.messages] == [Role.USER, Role.ASSISTANT]
    assert len(result.metrics) == 1


def test_run_returns_error_on_llm_exception() -> None:
    llm = BoomLLM(RuntimeError("network down"))
    runner = _make_runner(llm)

    result = runner.run(state=State())

    assert result.status is AgentStatus.ERROR
    assert "RuntimeError" in result.response
    assert "network down" in result.response
    assert [m.role for m in result.messages] == [Role.USER]
    assert result.metrics == []


def test_run_returns_error_on_prompt_provider_exception() -> None:
    provider = BoomPromptProvider(RuntimeError("no template"))
    runner = _make_runner(FakeLLM([_final_reply()]), provider=provider)

    result = runner.run(state=State())

    assert result.status is AgentStatus.ERROR
    assert "RuntimeError" in result.response
    assert "no template" in result.response
    assert result.messages == []
    assert result.metrics == []


def test_run_error_response_includes_exception_type_and_message() -> None:
    tool = BoomTool("t", KeyError("missing-key"))
    llm = FakeLLM([_tool_reply("t", {})])
    runner = _make_runner(llm, tools=[tool])

    result = runner.run(state=State())

    assert result.status is AgentStatus.ERROR
    assert result.response == "KeyError: 'missing-key'"


# ---------- run: FSM transitions ----------


def test_run_marks_running_then_success_on_final_reply() -> None:
    fsm = FakeAgentFSM()
    runner = _make_runner(FakeLLM([_final_reply()]), fsm=fsm)

    runner.run(state=State())

    assert fsm.transitions == ["running", "success"]
    assert fsm.status is AgentStatus.SUCCESS


def test_run_marks_running_then_error_on_exception() -> None:
    fsm = FakeAgentFSM()
    runner = _make_runner(BoomLLM(RuntimeError("boom")), fsm=fsm)

    runner.run(state=State())

    assert fsm.transitions == ["running", "error"]
    assert fsm.status is AgentStatus.ERROR


def test_run_marks_success_after_max_iterations() -> None:
    fsm = FakeAgentFSM()
    llm = FakeLLM([_tool_reply("t", {}), _final_reply("done")])
    tool = FakeTool("t")
    runner = _make_runner(llm, tools=[tool], max_iterations=1, fsm=fsm)

    runner.run(state=State())

    assert fsm.transitions == ["running", "success"]


# ---------- run: max_iterations ----------


def test_run_calls_final_user_after_max_iterations() -> None:
    provider = FakePromptProvider(final="FINAL_INSTRUCTION")
    tool = FakeTool("t")
    llm = FakeLLM(
        [
            _tool_reply("t", {}),
            _tool_reply("t", {}),
            _final_reply("wrapped up"),
        ]
    )
    runner = _make_runner(
        llm,
        provider=provider,
        tools=[tool],
        max_iterations=2,
    )

    result = runner.run(state=State())

    assert result.status is AgentStatus.SUCCESS
    assert result.response == "wrapped up"
    assert len(llm.calls) == 3
    last_messages, last_tools = llm.calls[2]
    assert last_tools == []
    assert last_messages[-1].role is Role.USER
    assert last_messages[-1].content == "FINAL_INSTRUCTION"


def test_run_max_iterations_zero_skips_loop_and_requests_final() -> None:
    provider = FakePromptProvider(final="FINAL")
    llm = FakeLLM([_final_reply("ok")])
    runner = _make_runner(
        llm,
        provider=provider,
        tools=[],
        max_iterations=0,
    )

    result = runner.run(state=State())

    assert result.status is AgentStatus.SUCCESS
    assert result.response == "ok"
    assert len(llm.calls) == 1
    last_messages, last_tools = llm.calls[0]
    assert last_tools == []
    assert last_messages[-1].role is Role.USER
    assert last_messages[-1].content == "FINAL"


def test_run_metrics_accumulate_across_iterations() -> None:
    tool = FakeTool("t")
    llm = FakeLLM(
        [
            _tool_reply("t", {}),
            _final_reply(),
        ]
    )
    runner = _make_runner(llm, tools=[tool])

    result = runner.run(state=State())

    assert len(result.metrics) == 2
