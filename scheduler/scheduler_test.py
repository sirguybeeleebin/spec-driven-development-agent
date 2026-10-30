# scheduler/scheduler_test.py

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from models import Task, WorkflowStatus
from scheduler.scheduler import Scheduler

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
    statuses: dict[str, WorkflowStatus] = field(default_factory=dict)

    @property
    def graph(self) -> FakeGraph:
        return FakeGraph(edges=self.edges)


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


def _workflow(
    task_ids: list[str],
    edges: list[tuple[str, str]] | None = None,
    statuses: dict[str, WorkflowStatus] | None = None,
) -> FakeWorkflow:
    tasks = [_task(t) for t in task_ids]
    if statuses is None:
        statuses = {t.task_id: WorkflowStatus.IDLE for t in tasks}
    return FakeWorkflow(
        tasks=tasks,
        edges=[FakeEdge(s, d) for s, d in (edges or [])],
        statuses=statuses,
    )


@pytest.fixture
def scheduler() -> Scheduler:
    return Scheduler()


def _ids(tasks: list[Task]) -> list[str]:
    return [t.task_id for t in tasks]


# ---- empty / trivial ----


def test_empty_workflow_returns_empty(scheduler: Scheduler) -> None:
    wf = _workflow([])
    assert scheduler.get_ready_tasks(wf) == []


def test_single_idle_no_ancestors_is_ready(scheduler: Scheduler) -> None:
    wf = _workflow(["a"])
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["a"]
    # status stays IDLE — scheduler only mutates when not ready
    assert wf.statuses["a"] is WorkflowStatus.IDLE


def test_single_hold_no_ancestors_is_ready(scheduler: Scheduler) -> None:
    wf = _workflow(["a"], statuses={"a": WorkflowStatus.HOLD})
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["a"]
    # HOLD stays HOLD when it becomes ready
    assert wf.statuses["a"] is WorkflowStatus.HOLD


# ---- ancestor gating ----


def test_idle_task_with_pending_ancestor_becomes_hold(
    scheduler: Scheduler,
) -> None:
    wf = _workflow(["a", "b"], edges=[("a", "b")])
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["a"]
    assert wf.statuses["a"] is WorkflowStatus.IDLE
    assert wf.statuses["b"] is WorkflowStatus.HOLD


def test_idle_task_with_success_ancestor_is_ready(
    scheduler: Scheduler,
) -> None:
    wf = _workflow(
        ["a", "b"],
        edges=[("a", "b")],
        statuses={"a": WorkflowStatus.SUCCESS, "b": WorkflowStatus.IDLE},
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["b"]


def test_idle_task_with_error_ancestor_becomes_hold_not_error(
    scheduler: Scheduler,
) -> None:
    wf = _workflow(
        ["a", "b"],
        edges=[("a", "b")],
        statuses={"a": WorkflowStatus.ERROR, "b": WorkflowStatus.IDLE},
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == []
    # Scheduler does NOT turn ERROR-ancestor descendants into ERROR
    assert wf.statuses["b"] is WorkflowStatus.HOLD


def test_idle_task_with_running_ancestor_becomes_hold(
    scheduler: Scheduler,
) -> None:
    wf = _workflow(
        ["a", "b"],
        edges=[("a", "b")],
        statuses={"a": WorkflowStatus.RUNNING, "b": WorkflowStatus.IDLE},
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == []
    assert wf.statuses["b"] is WorkflowStatus.HOLD


def test_hold_task_with_pending_ancestor_stays_hold(
    scheduler: Scheduler,
) -> None:
    wf = _workflow(
        ["a", "b"],
        edges=[("a", "b")],
        statuses={"a": WorkflowStatus.RUNNING, "b": WorkflowStatus.HOLD},
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == []
    # HOLD is not re-transitioned to HOLD
    assert wf.statuses["b"] is WorkflowStatus.HOLD


def test_hold_task_with_success_ancestor_is_ready(
    scheduler: Scheduler,
) -> None:
    wf = _workflow(
        ["a", "b"],
        edges=[("a", "b")],
        statuses={"a": WorkflowStatus.SUCCESS, "b": WorkflowStatus.HOLD},
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["b"]


def test_hold_task_with_error_ancestor_stays_hold(
    scheduler: Scheduler,
) -> None:
    # WorkflowRunner converts stuck HOLD to ERROR at the end; Scheduler
    # leaves ERROR-ancestor descendants in HOLD.
    wf = _workflow(
        ["a", "b"],
        edges=[("a", "b")],
        statuses={"a": WorkflowStatus.ERROR, "b": WorkflowStatus.HOLD},
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == []
    assert wf.statuses["b"] is WorkflowStatus.HOLD


# ---- skipped statuses ----


def test_success_task_is_skipped(scheduler: Scheduler) -> None:
    wf = _workflow(["a"], statuses={"a": WorkflowStatus.SUCCESS})
    assert scheduler.get_ready_tasks(wf) == []
    assert wf.statuses["a"] is WorkflowStatus.SUCCESS


def test_running_task_is_skipped(scheduler: Scheduler) -> None:
    wf = _workflow(["a"], statuses={"a": WorkflowStatus.RUNNING})
    assert scheduler.get_ready_tasks(wf) == []
    assert wf.statuses["a"] is WorkflowStatus.RUNNING


def test_error_task_is_skipped(scheduler: Scheduler) -> None:
    wf = _workflow(["a"], statuses={"a": WorkflowStatus.ERROR})
    assert scheduler.get_ready_tasks(wf) == []
    assert wf.statuses["a"] is WorkflowStatus.ERROR


# ---- ordering ----


def test_ready_preserves_workflow_tasks_order(scheduler: Scheduler) -> None:
    wf = _workflow(["c", "a", "b"])
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["c", "a", "b"]


def test_multiple_ready_tasks_in_one_call(scheduler: Scheduler) -> None:
    wf = _workflow(["a", "b", "c"])
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["a", "b", "c"]


# ---- chain ----


def test_chain_first_scan(scheduler: Scheduler) -> None:
    wf = _workflow(["a", "b", "c"], edges=[("a", "b"), ("b", "c")])
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["a"]
    assert wf.statuses["b"] is WorkflowStatus.HOLD
    assert wf.statuses["c"] is WorkflowStatus.HOLD


def test_chain_second_scan(scheduler: Scheduler) -> None:
    wf = _workflow(
        ["a", "b", "c"],
        edges=[("a", "b"), ("b", "c")],
        statuses={
            "a": WorkflowStatus.SUCCESS,
            "b": WorkflowStatus.HOLD,
            "c": WorkflowStatus.HOLD,
        },
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["b"]
    # c still has b pending
    assert wf.statuses["c"] is WorkflowStatus.HOLD


def test_chain_third_scan(scheduler: Scheduler) -> None:
    wf = _workflow(
        ["a", "b", "c"],
        edges=[("a", "b"), ("b", "c")],
        statuses={
            "a": WorkflowStatus.SUCCESS,
            "b": WorkflowStatus.SUCCESS,
            "c": WorkflowStatus.HOLD,
        },
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["c"]


# ---- fan-out / fan-in ----


def test_fan_out_first_scan(scheduler: Scheduler) -> None:
    wf = _workflow(
        ["root", "l", "r"],
        edges=[("root", "l"), ("root", "r")],
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["root"]
    assert wf.statuses["l"] is WorkflowStatus.HOLD
    assert wf.statuses["r"] is WorkflowStatus.HOLD


def test_fan_out_after_root_success(scheduler: Scheduler) -> None:
    wf = _workflow(
        ["root", "l", "r"],
        edges=[("root", "l"), ("root", "r")],
        statuses={
            "root": WorkflowStatus.SUCCESS,
            "l": WorkflowStatus.HOLD,
            "r": WorkflowStatus.HOLD,
        },
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["l", "r"]


def test_fan_in_waits_for_all_parents(scheduler: Scheduler) -> None:
    wf = _workflow(
        ["a", "b", "c"],
        edges=[("a", "c"), ("b", "c")],
        statuses={
            "a": WorkflowStatus.SUCCESS,
            "b": WorkflowStatus.RUNNING,
            "c": WorkflowStatus.HOLD,
        },
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == []
    assert wf.statuses["c"] is WorkflowStatus.HOLD


def test_fan_in_ready_when_both_parents_success(
    scheduler: Scheduler,
) -> None:
    wf = _workflow(
        ["a", "b", "c"],
        edges=[("a", "c"), ("b", "c")],
        statuses={
            "a": WorkflowStatus.SUCCESS,
            "b": WorkflowStatus.SUCCESS,
            "c": WorkflowStatus.HOLD,
        },
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["c"]


def test_fan_in_stuck_when_one_parent_error(scheduler: Scheduler) -> None:
    wf = _workflow(
        ["a", "b", "c"],
        edges=[("a", "c"), ("b", "c")],
        statuses={
            "a": WorkflowStatus.SUCCESS,
            "b": WorkflowStatus.ERROR,
            "c": WorkflowStatus.HOLD,
        },
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == []
    # stays HOLD — WorkflowRunner will convert to ERROR at end
    assert wf.statuses["c"] is WorkflowStatus.HOLD


# ---- cycles ----


def test_cycle_both_become_hold(scheduler: Scheduler) -> None:
    wf = _workflow(
        ["a", "b"],
        edges=[("a", "b"), ("b", "a")],
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == []
    assert wf.statuses["a"] is WorkflowStatus.HOLD
    assert wf.statuses["b"] is WorkflowStatus.HOLD


def test_self_loop_becomes_hold(scheduler: Scheduler) -> None:
    wf = _workflow(["a"], edges=[("a", "a")])
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == []
    assert wf.statuses["a"] is WorkflowStatus.HOLD


def test_cycle_with_independent_root(scheduler: Scheduler) -> None:
    # root has no ancestors → ready; cycle members → HOLD
    wf = _workflow(
        ["root", "a", "b"],
        edges=[("a", "b"), ("b", "a")],
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["root"]
    assert wf.statuses["a"] is WorkflowStatus.HOLD
    assert wf.statuses["b"] is WorkflowStatus.HOLD


# ---- diamond ----


def test_diamond_first_scan(scheduler: Scheduler) -> None:
    wf = _workflow(
        ["a", "b", "c", "d"],
        edges=[("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")],
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["a"]
    assert wf.statuses["b"] is WorkflowStatus.HOLD
    assert wf.statuses["c"] is WorkflowStatus.HOLD
    assert wf.statuses["d"] is WorkflowStatus.HOLD


def test_diamond_after_a_success(scheduler: Scheduler) -> None:
    wf = _workflow(
        ["a", "b", "c", "d"],
        edges=[("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")],
        statuses={
            "a": WorkflowStatus.SUCCESS,
            "b": WorkflowStatus.HOLD,
            "c": WorkflowStatus.HOLD,
            "d": WorkflowStatus.HOLD,
        },
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == ["b", "c"]


def test_diamond_d_waits_for_both(scheduler: Scheduler) -> None:
    wf = _workflow(
        ["a", "b", "c", "d"],
        edges=[("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")],
        statuses={
            "a": WorkflowStatus.SUCCESS,
            "b": WorkflowStatus.SUCCESS,
            "c": WorkflowStatus.RUNNING,
            "d": WorkflowStatus.HOLD,
        },
    )
    ready = scheduler.get_ready_tasks(wf)
    assert _ids(ready) == []
    assert wf.statuses["d"] is WorkflowStatus.HOLD


# ---- idempotence ----


def test_repeated_calls_do_not_change_hold_tasks(
    scheduler: Scheduler,
) -> None:
    wf = _workflow(
        ["a", "b"],
        edges=[("a", "b")],
        statuses={"a": WorkflowStatus.RUNNING, "b": WorkflowStatus.HOLD},
    )
    scheduler.get_ready_tasks(wf)
    assert wf.statuses["b"] is WorkflowStatus.HOLD
    scheduler.get_ready_tasks(wf)
    assert wf.statuses["b"] is WorkflowStatus.HOLD
