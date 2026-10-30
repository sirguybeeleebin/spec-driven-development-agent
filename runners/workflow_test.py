# runners/workflow_test.py

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from fsms.workflow import WorkflowFSM
from models import (
    Task,
    TaskResult,
    TaskStatus,
    WorkflowResult,
    WorkflowStatus,
)
from runners.workflow import WorkflowRunner
from scheduler import Scheduler

# ---- fakes for the workflow structure ----


@dataclass
class FakeEdge:
    source_task_id: str
    target_task_id: str

    @property
    def source(self) -> SimpleNamespace:
        return SimpleNamespace(task_id=self.source_task_id)

    @property
    def target(self) -> SimpleNamespace:
        return SimpleNamespace(task_id=self.target_task_id)


@dataclass
class FakeGraph:
    edges: list[FakeEdge] = field(default_factory=list)


@dataclass
class FakeWorkflow:
    tasks: list[Task]
    edges: list[FakeEdge] = field(default_factory=list)

    @property
    def graph(self) -> FakeGraph:
        return FakeGraph(edges=self.edges)

    @property
    def statuses(self) -> dict[str, WorkflowStatus]:
        return self._statuses

    def __post_init__(self) -> None:
        self._statuses: dict[str, WorkflowStatus] = {
            t.task_id: WorkflowStatus.IDLE for t in self.tasks
        }


class FakeTaskRunner:
    def __init__(
        self,
        outcomes: dict[str, TaskResult] | None = None,
    ) -> None:
        self._outcomes = dict(outcomes or {})
        self.calls: list[str] = []

    def run(self, task: Task) -> TaskResult:
        self.calls.append(task.task_id)
        outcome = self._outcomes.get(task.task_id)
        if outcome is None:
            return _success(task.task_id)
        return outcome


class RaisingTaskRunner:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.calls: list[str] = []

    def run(self, task: Task) -> TaskResult:
        self.calls.append(task.task_id)
        raise self._exc


# ---- helpers ----


def _task(task_id: str) -> Task:
    return Task(
        task_id=task_id,
        goal="g",
        target_file=f"{task_id}.py",
        target_test_file=f"{task_id}_test.py",
        declares=[],
        interfaces=[],
        gherkins=[],
        constitution="",
    )


def _success(task_id: str) -> TaskResult:
    return TaskResult(
        task_id=task_id,
        status=TaskStatus.SUCCESS,
        results=[],
    )


def _error(task_id: str) -> TaskResult:
    return TaskResult(
        task_id=task_id,
        status=TaskStatus.ERROR,
        results=[],
    )


def _workflow(
    task_ids: list[str],
    edges: list[tuple[str, str]] | None = None,
) -> FakeWorkflow:
    return FakeWorkflow(
        tasks=[_task(t) for t in task_ids],
        edges=[FakeEdge(s, d) for s, d in (edges or [])],
    )


def _runner(
    outcomes: dict[str, TaskResult] | None = None,
) -> tuple[WorkflowRunner, FakeTaskRunner]:
    fake = FakeTaskRunner(outcomes)
    runner = WorkflowRunner(
        task_runner=fake,
        scheduler=Scheduler(),
        fsm_factory=WorkflowFSM,
    )
    return runner, fake


# ---- empty / trivial workflows ----


def test_empty_workflow_returns_empty_result() -> None:
    wf = _workflow([])
    runner, fake = _runner()

    result = runner.run(wf)

    assert isinstance(result, WorkflowResult)
    assert result.results == []
    assert fake.calls == []


def test_single_task_no_edges_runs_once() -> None:
    wf = _workflow(["a"])
    runner, fake = _runner()

    result = runner.run(wf)

    assert fake.calls == ["a"]
    assert len(result.results) == 1
    assert result.results[0].status is TaskStatus.SUCCESS
    assert wf.statuses["a"] is WorkflowStatus.SUCCESS


def test_single_task_error_propagates_to_result() -> None:
    wf = _workflow(["a"])
    runner, _ = _runner({"a": _error("a")})

    result = runner.run(wf)

    assert result.results[0].status is TaskStatus.ERROR
    assert wf.statuses["a"] is WorkflowStatus.ERROR


# ---- linear chain ----


def test_linear_chain_runs_in_order() -> None:
    wf = _workflow(["a", "b", "c"], [("a", "b"), ("b", "c")])
    runner, fake = _runner()

    runner.run(wf)

    assert fake.calls == ["a", "b", "c"]
    assert all(s is WorkflowStatus.SUCCESS for s in wf.statuses.values())


def test_linear_chain_stops_on_first_error() -> None:
    wf = _workflow(["a", "b", "c"], [("a", "b"), ("b", "c")])
    runner, fake = _runner({"a": _error("a")})

    result = runner.run(wf)

    assert fake.calls == ["a"]
    assert wf.statuses["a"] is WorkflowStatus.ERROR
    assert wf.statuses["b"] is WorkflowStatus.ERROR
    assert wf.statuses["c"] is WorkflowStatus.ERROR
    statuses = [r.status for r in result.results]
    assert statuses.count(TaskStatus.ERROR) == 3


# ---- fan-out / fan-in ----


def test_fan_out_runs_both_children() -> None:
    wf = _workflow(
        ["root", "l", "r"],
        [("root", "l"), ("root", "r")],
    )
    runner, fake = _runner()

    runner.run(wf)

    assert fake.calls == ["root", "l", "r"]
    assert all(s is WorkflowStatus.SUCCESS for s in wf.statuses.values())


def test_fan_in_waits_for_all_parents() -> None:
    wf = _workflow(
        ["a", "b", "c"],
        [("a", "c"), ("b", "c")],
    )
    runner, fake = _runner()

    runner.run(wf)

    assert fake.calls == ["a", "b", "c"]
    assert wf.statuses["c"] is WorkflowStatus.SUCCESS


def test_fan_in_marks_error_when_one_parent_errors() -> None:
    wf = _workflow(
        ["a", "b", "c"],
        [("a", "c"), ("b", "c")],
    )
    runner, fake = _runner({"a": _error("a")})

    runner.run(wf)

    assert "a" in fake.calls
    assert "b" in fake.calls
    assert "c" not in fake.calls
    assert wf.statuses["c"] is WorkflowStatus.ERROR


# ---- error results from TaskRunner ----


def test_error_result_does_not_stop_independent_tasks() -> None:
    wf = _workflow(["a", "b"])
    runner, fake = _runner({"a": _error("a")})

    runner.run(wf)

    assert fake.calls == ["a", "b"]
    assert wf.statuses["a"] is WorkflowStatus.ERROR
    assert wf.statuses["b"] is WorkflowStatus.SUCCESS


# ---- runner contract: exceptions propagate ----


def test_runner_exception_propagates() -> None:
    wf = _workflow(["a"])
    raising = RaisingTaskRunner(RuntimeError("boom"))
    runner = WorkflowRunner(
        task_runner=raising,
        scheduler=Scheduler(),
        fsm_factory=WorkflowFSM,
    )

    with pytest.raises(RuntimeError, match="boom"):
        runner.run(wf)

    assert raising.calls == ["a"]
    assert wf.statuses["a"] is WorkflowStatus.RUNNING


# ---- cycles / stuck states ----


def test_cycle_marks_all_members_as_error() -> None:
    wf = _workflow(
        ["a", "b"],
        [("a", "b"), ("b", "a")],
    )
    runner, fake = _runner()

    result = runner.run(wf)

    assert fake.calls == []
    assert wf.statuses["a"] is WorkflowStatus.ERROR
    assert wf.statuses["b"] is WorkflowStatus.ERROR
    statuses = sorted(r.status for r in result.results)
    assert statuses == [TaskStatus.ERROR, TaskStatus.ERROR]


def test_self_loop_marks_task_error() -> None:
    wf = _workflow(["a"], [("a", "a")])
    runner, fake = _runner()

    runner.run(wf)

    assert fake.calls == []
    assert wf.statuses["a"] is WorkflowStatus.ERROR


def test_isolated_stuck_component_after_successful_root() -> None:
    wf = _workflow(
        ["root", "b", "c"],
        [("b", "c"), ("c", "b")],
    )
    runner, fake = _runner()

    runner.run(wf)

    assert fake.calls == ["root"]
    assert wf.statuses["root"] is WorkflowStatus.SUCCESS
    assert wf.statuses["b"] is WorkflowStatus.ERROR
    assert wf.statuses["c"] is WorkflowStatus.ERROR


# ---- result aggregation ----


def test_result_status_counts_match_task_outcomes() -> None:
    wf = _workflow(
        ["a", "b", "c"],
        [("a", "b")],
    )
    runner, _ = _runner({"a": _error("a")})

    result = runner.run(wf)

    statuses = [r.status for r in result.results]
    assert statuses.count(TaskStatus.SUCCESS) == 1  # c
    assert statuses.count(TaskStatus.ERROR) == 2  # a, b


def test_each_task_yields_exactly_one_result() -> None:
    wf = _workflow(
        ["a", "b", "c"],
        [("a", "b"), ("b", "c")],
    )
    runner, _ = _runner()

    result = runner.run(wf)

    ids = [r.task_id for r in result.results]
    assert sorted(ids) == ["a", "b", "c"]
    assert len(ids) == len(set(ids))


def test_workflow_statuses_all_terminal_at_end() -> None:
    wf = _workflow(
        ["a", "b", "c", "d"],
        [("a", "b"), ("b", "c")],
    )
    runner, _ = _runner({"b": _error("b")})

    runner.run(wf)

    for tid, st in wf.statuses.items():
        assert st in (
            WorkflowStatus.SUCCESS,
            WorkflowStatus.ERROR,
        ), f"task {tid} ended in {st}"


# ---- idempotence / restart ----


def test_already_success_task_is_skipped() -> None:
    wf = _workflow(["a", "b"], [("a", "b")])
    wf._statuses["a"] = WorkflowStatus.SUCCESS
    runner, fake = _runner()

    runner.run(wf)

    assert fake.calls == ["b"]
    assert wf.statuses["b"] is WorkflowStatus.SUCCESS
