# runners/task_test.py

from __future__ import annotations

import copy
import dataclasses
import re
from pathlib import Path

import pytest

from models import (
    AgentResult,
    AgentStatus,
    Gherkin,
    State,
    Task,
    TaskStatus,
    TestResult,
)
from runners.task import TaskRunner

# ---- fakes ----


class FakeTaskFSM:
    def __init__(self) -> None:
        self._status = TaskStatus.IDLE
        self.transitions: list[str] = []

    @property
    def status(self) -> TaskStatus:
        return self._status

    def mark_running(self) -> None:
        self.transitions.append("running")
        self._status = TaskStatus.RUNNING

    def mark_success(self) -> None:
        self.transitions.append("success")
        self._status = TaskStatus.SUCCESS

    def mark_error(self) -> None:
        self.transitions.append("error")
        self._status = TaskStatus.ERROR


class FakeAgent:
    def __init__(
        self,
        response: str = "",
        status: AgentStatus = AgentStatus.SUCCESS,
        delete_on_call: Path | None = None,
    ) -> None:
        self._response = response
        self._status = status
        self._delete_on_call = delete_on_call
        self.calls: list[State] = []

    def run(self, *, state: State) -> AgentResult:
        self.calls.append(copy.copy(state))
        if self._delete_on_call is not None and self._delete_on_call.exists():
            self._delete_on_call.unlink()
        return AgentResult(
            status=self._status,
            response=self._response,
            messages=[],
            metrics=[],
        )


class FakeTestRunner:
    def __init__(self, results: list[TestResult] | None = None) -> None:
        self._results = list(results or [])
        self.test_function_calls: list[str] = []
        self.run_calls: list[str] = []

    def test_function(self, state: State) -> str:
        assert state.gherkin is not None
        self.test_function_calls.append(state.gherkin.name)
        slug = re.sub(r"[^\w]+", "_", state.gherkin.name).strip("_").lower()
        return f"test_{slug}"

    def run(self, state: State) -> TestResult:
        self.run_calls.append(state.test_function)
        if self._results:
            return self._results.pop(0)
        return TestResult(passed=True, output="")


# ---- helpers ----


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _gherkin(name: str = "scenario", target: str = "X") -> Gherkin:
    return Gherkin(
        name=name,
        target_declaration=target,
        given=["g"],
        when=["w"],
        then=["t"],
    )


def _task(
    task_id: str = "t1",
    target_file: str = "src.py",
    target_test_file: str = "src_test.py",
    gherkins: list[Gherkin] | None = None,
) -> Task:
    return Task(
        task_id=task_id,
        goal="do the thing",
        target_file=target_file,
        target_test_file=target_test_file,
        declares=[],
        interfaces=[],
        gherkins=gherkins or [],
        constitution="",
    )


def _make_runner(
    *,
    researcher: FakeAgent | None = None,
    implementer: FakeAgent | None = None,
    tester: FakeAgent | None = None,
    fixer: FakeAgent | None = None,
    testrunner: FakeTestRunner | None = None,
    max_fix_attempts: int = 2,
    fsm: FakeTaskFSM | None = None,
) -> TaskRunner:
    return TaskRunner(
        researcher=researcher or FakeAgent(),
        implementer=implementer or FakeAgent(),
        tester=tester or FakeAgent(),
        fixer=fixer or FakeAgent(),
        testrunner=testrunner or FakeTestRunner(),
        max_fix_attempts=max_fix_attempts,
        fsm=fsm or FakeTaskFSM(),
    )


# ---- contract: State fields used by TaskRunner ----


def test_state_fields_used_by_task_runner_exist() -> None:
    field_names = {f.name for f in dataclasses.fields(State)}
    required = {
        "researcher_summary",
        "implementer_summary",
        "tester_summary",
        "test_result",
        "gherkin",
        "target_declaration",
        "test_function",
    }
    missing = required - field_names
    assert not missing, f"State is missing fields used by TaskRunner: {missing}"


# ---- FSM transitions ----


def test_success_marks_running_then_success(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    fsm = FakeTaskFSM()
    runner = _make_runner(fsm=fsm)

    runner.run(_task(gherkins=[]))

    assert fsm.transitions == ["running", "success"]
    assert fsm.status is TaskStatus.SUCCESS


def test_researcher_error_marks_running_then_error(workspace: Path) -> None:
    fsm = FakeTaskFSM()
    runner = _make_runner(
        researcher=FakeAgent(status=AgentStatus.ERROR),
        fsm=fsm,
    )

    runner.run(_task())

    assert fsm.transitions == ["running", "error"]
    assert fsm.status is TaskStatus.ERROR


# ---- agent errors become TaskStatus.ERROR ----


def test_researcher_error_returns_error_result() -> None:
    runner = _make_runner(
        researcher=FakeAgent(status=AgentStatus.ERROR, response="boom")
    )
    result = runner.run(_task())

    assert result.status is TaskStatus.ERROR
    assert len(result.results) == 1


def test_implementer_error_returns_error_result() -> None:
    runner = _make_runner(
        implementer=FakeAgent(status=AgentStatus.ERROR, response="boom")
    )
    result = runner.run(_task())

    assert result.status is TaskStatus.ERROR
    assert len(result.results) == 2


def test_tester_error_returns_error_result(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    tester = FakeAgent(status=AgentStatus.ERROR, response="boom")
    testrunner = FakeTestRunner()
    runner = _make_runner(tester=tester, testrunner=testrunner)

    result = runner.run(_task(gherkins=[_gherkin("a")]))

    assert result.status is TaskStatus.ERROR
    assert testrunner.run_calls == []


def test_fixer_error_returns_error_result(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    testrunner = FakeTestRunner(results=[TestResult(passed=False, output="fail")])
    fixer = FakeAgent(status=AgentStatus.ERROR, response="boom")
    runner = _make_runner(fixer=fixer, testrunner=testrunner)

    result = runner.run(_task(gherkins=[_gherkin("a")]))

    assert result.status is TaskStatus.ERROR
    assert len(testrunner.run_calls) == 1


def test_error_result_keeps_prior_results(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    researcher = FakeAgent(response="r")
    implementer = FakeAgent(response="i")
    tester = FakeAgent(status=AgentStatus.ERROR, response="boom")
    runner = _make_runner(
        researcher=researcher,
        implementer=implementer,
        tester=tester,
    )

    result = runner.run(_task(gherkins=[_gherkin("a")]))

    assert result.status is TaskStatus.ERROR
    assert len(result.results) == 3


# ---- target file missing ----


def test_target_file_missing_returns_error(workspace: Path) -> None:
    runner = _make_runner()
    result = runner.run(_task(gherkins=[_gherkin("a")]))

    assert result.status is TaskStatus.ERROR
    assert len(result.results) == 2


def test_target_file_missing_skips_all_gherkins(workspace: Path) -> None:
    tester = FakeAgent()
    testrunner = FakeTestRunner()
    runner = _make_runner(tester=tester, testrunner=testrunner)

    runner.run(_task(gherkins=[_gherkin("a"), _gherkin("b")]))

    assert tester.calls == []
    assert testrunner.test_function_calls == []
    assert testrunner.run_calls == []


# ---- happy paths ----


def test_empty_gherkins_still_success(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    runner = _make_runner()
    result = runner.run(_task(gherkins=[]))

    assert result.status is TaskStatus.SUCCESS


def test_gherkin_passes_first_try(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    testrunner = FakeTestRunner(results=[TestResult(passed=True, output="")])
    fixer = FakeAgent()
    runner = _make_runner(fixer=fixer, testrunner=testrunner)

    result = runner.run(_task(gherkins=[_gherkin("a")]))

    assert result.status is TaskStatus.SUCCESS
    assert fixer.calls == []
    assert testrunner.run_calls == ["test_a"]


def test_gherkin_passes_after_one_fix(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    testrunner = FakeTestRunner(
        results=[
            TestResult(passed=False, output="fail"),
            TestResult(passed=True, output=""),
        ]
    )
    fixer = FakeAgent()
    runner = _make_runner(fixer=fixer, testrunner=testrunner)

    result = runner.run(_task(gherkins=[_gherkin("a")]))

    assert result.status is TaskStatus.SUCCESS
    assert len(fixer.calls) == 1
    assert testrunner.run_calls == ["test_a", "test_a"]


def test_multiple_gherkins_all_pass(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    testrunner = FakeTestRunner(
        results=[
            TestResult(passed=True, output=""),
            TestResult(passed=True, output=""),
        ]
    )
    runner = _make_runner(testrunner=testrunner)

    result = runner.run(_task(gherkins=[_gherkin("a"), _gherkin("b")]))

    assert result.status is TaskStatus.SUCCESS
    assert testrunner.test_function_calls == ["a", "b"]
    assert testrunner.run_calls == ["test_a", "test_b"]


def test_result_carries_task_id(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    runner = _make_runner()
    result = runner.run(_task(task_id="abc"))

    assert result.task_id == "abc"


# ---- failure modes that still yield SUCCESS ----


def test_gherkin_fails_after_max_attempts_still_success(
    workspace: Path,
) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    fail = TestResult(passed=False, output="fail")
    testrunner = FakeTestRunner(results=[fail, fail, fail])
    fixer = FakeAgent()
    runner = _make_runner(fixer=fixer, testrunner=testrunner, max_fix_attempts=2)

    result = runner.run(_task(gherkins=[_gherkin("a")]))

    assert result.status is TaskStatus.SUCCESS
    assert len(fixer.calls) == 2
    assert len(testrunner.run_calls) == 3


def test_all_gherkins_fail_still_success(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    fail = TestResult(passed=False, output="fail")
    testrunner = FakeTestRunner(results=[fail] * 6)
    fixer = FakeAgent()
    runner = _make_runner(fixer=fixer, testrunner=testrunner, max_fix_attempts=2)

    result = runner.run(_task(gherkins=[_gherkin("a"), _gherkin("b")]))

    assert result.status is TaskStatus.SUCCESS
    assert len(fixer.calls) == 4
    assert len(testrunner.run_calls) == 6


def test_max_fix_attempts_zero_skips_fixer(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    testrunner = FakeTestRunner(results=[TestResult(passed=False, output="fail")])
    fixer = FakeAgent()
    runner = _make_runner(fixer=fixer, testrunner=testrunner, max_fix_attempts=0)

    result = runner.run(_task(gherkins=[_gherkin("a")]))

    assert result.status is TaskStatus.SUCCESS
    assert fixer.calls == []
    assert len(testrunner.run_calls) == 1


# ---- failure modes that skip a gherkin ----


def test_test_file_missing_after_tester_skips_gherkins(
    workspace: Path,
) -> None:
    (workspace / "src.py").write_text("")
    testrunner = FakeTestRunner()
    runner = _make_runner(testrunner=testrunner)

    result = runner.run(_task(gherkins=[_gherkin("a"), _gherkin("b")]))

    assert result.status is TaskStatus.SUCCESS
    assert testrunner.test_function_calls == ["a", "b"]
    assert testrunner.run_calls == []


def test_test_file_disappears_after_fixer_breaks_loop(
    workspace: Path,
) -> None:
    (workspace / "src.py").write_text("")
    test_path = workspace / "src_test.py"
    test_path.write_text("")
    testrunner = FakeTestRunner(results=[TestResult(passed=False, output="fail")])
    fixer = FakeAgent(delete_on_call=test_path)
    runner = _make_runner(fixer=fixer, testrunner=testrunner)

    result = runner.run(_task(gherkins=[_gherkin("a")]))

    assert result.status is TaskStatus.SUCCESS
    assert len(fixer.calls) == 1
    assert len(testrunner.run_calls) == 1


# ---- state propagation ----


def test_state_researcher_summary_visible_to_tester(
    workspace: Path,
) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    researcher = FakeAgent(response="research output")
    tester = FakeAgent()
    testrunner = FakeTestRunner(results=[TestResult(passed=True, output="")])
    runner = _make_runner(researcher=researcher, tester=tester, testrunner=testrunner)

    runner.run(_task(gherkins=[_gherkin("a")]))

    assert tester.calls[0].researcher_summary == "research output"


def test_state_implementer_summary_visible_to_tester(
    workspace: Path,
) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    implementer = FakeAgent(response="impl output")
    tester = FakeAgent()
    testrunner = FakeTestRunner(results=[TestResult(passed=True, output="")])
    runner = _make_runner(implementer=implementer, tester=tester, testrunner=testrunner)

    runner.run(_task(gherkins=[_gherkin("a")]))

    assert tester.calls[0].implementer_summary == "impl output"


def test_state_tester_summary_visible_to_fixer(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    tester = FakeAgent(response="tester output")
    fixer = FakeAgent()
    testrunner = FakeTestRunner(
        results=[
            TestResult(passed=False, output="fail"),
            TestResult(passed=True, output=""),
        ]
    )
    runner = _make_runner(tester=tester, fixer=fixer, testrunner=testrunner)

    runner.run(_task(gherkins=[_gherkin("a")]))

    assert fixer.calls[0].tester_summary == "tester output"


def test_state_gherkin_and_test_function_set_for_tester(
    workspace: Path,
) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    tester = FakeAgent()
    testrunner = FakeTestRunner(results=[TestResult(passed=True, output="")])
    runner = _make_runner(tester=tester, testrunner=testrunner)
    g = _gherkin("get returns product", target="ProductRepository")

    runner.run(_task(gherkins=[g]))

    captured = tester.calls[0]
    assert captured.gherkin is g
    assert captured.target_declaration == "ProductRepository"
    assert captured.test_function == "test_get_returns_product"


def test_state_test_result_set_before_fixer(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    first_fail = TestResult(passed=False, output="fail1")
    testrunner = FakeTestRunner(
        results=[first_fail, TestResult(passed=True, output="")]
    )
    fixer = FakeAgent()
    runner = _make_runner(fixer=fixer, testrunner=testrunner)

    runner.run(_task(gherkins=[_gherkin("a")]))

    assert fixer.calls[0].test_result is first_fail


# ---- call counts ----


def test_agent_call_counts_happy_path(workspace: Path) -> None:
    (workspace / "src.py").write_text("")
    (workspace / "src_test.py").write_text("")
    researcher = FakeAgent()
    implementer = FakeAgent()
    tester = FakeAgent()
    testrunner = FakeTestRunner(results=[TestResult(passed=True, output="")])
    runner = _make_runner(
        researcher=researcher,
        implementer=implementer,
        tester=tester,
        testrunner=testrunner,
    )

    runner.run(_task(gherkins=[_gherkin("a")]))

    assert len(researcher.calls) == 1
    assert len(implementer.calls) == 1
    assert len(tester.calls) == 1
    assert testrunner.test_function_calls == ["a"]
    assert testrunner.run_calls == ["test_a"]
