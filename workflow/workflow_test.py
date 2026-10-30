from __future__ import annotations

from models import Task
from workflow import Workflow


def _task(task_id: str) -> Task:
    return Task(
        task_id=task_id,
        goal=f"goal {task_id}",
        target=f"{task_id}.py",
        target_test=f"{task_id}_test.py",
        interfaces=[],
        scenarios=[],
    )


def workflow_empty_ready_test() -> None:
    print(f"[{__name__}] workflow_empty_ready_test")
    workflow = Workflow(tasks=[], edges=[])
    assert workflow.get_ready() == []


def workflow_single_task_ready_test() -> None:
    print(f"[{__name__}] workflow_single_task_ready_test")
    a = _task("A")
    workflow = Workflow(tasks=[a], edges=[])
    assert workflow.get_ready() == [a]


def workflow_independent_tasks_ready_test() -> None:
    print(f"[{__name__}] workflow_independent_tasks_ready_test")
    a = _task("A")
    b = _task("B")
    workflow = Workflow(tasks=[a, b], edges=[])
    assert workflow.get_ready() == [a, b]


def workflow_dependent_task_blocked_test() -> None:
    print(f"[{__name__}] workflow_dependent_task_blocked_test")
    a = _task("A")
    b = _task("B")
    workflow = Workflow(tasks=[a, b], edges=[(a, b)])
    assert workflow.get_ready() == [a]


def workflow_dependent_ready_after_success_test() -> None:
    print(f"[{__name__}] workflow_dependent_ready_after_success_test")
    a = _task("A")
    b = _task("B")
    workflow = Workflow(tasks=[a, b], edges=[(a, b)])
    workflow.mark_running(a)
    workflow.mark_success(a)
    assert workflow.get_ready() == [b]


def workflow_running_not_ready_test() -> None:
    print(f"[{__name__}] workflow_running_not_ready_test")
    a = _task("A")
    workflow = Workflow(tasks=[a], edges=[])
    workflow.mark_running(a)
    assert workflow.get_ready() == []


def workflow_done_not_ready_test() -> None:
    print(f"[{__name__}] workflow_done_not_ready_test")
    a = _task("A")
    workflow = Workflow(tasks=[a], edges=[])
    workflow.mark_running(a)
    workflow.mark_success(a)
    assert workflow.get_ready() == []


def workflow_failed_blocks_dependents_test() -> None:
    print(f"[{__name__}] workflow_failed_blocks_dependents_test")
    a = _task("A")
    b = _task("B")
    workflow = Workflow(tasks=[a, b], edges=[(a, b)])
    workflow.mark_running(a)
    workflow.mark_failed(a)
    assert workflow.get_ready() == []


def workflow_multiple_deps_test() -> None:
    print(f"[{__name__}] workflow_multiple_deps_test")
    a = _task("A")
    b = _task("B")
    c = _task("C")
    workflow = Workflow(tasks=[a, b, c], edges=[(a, c), (b, c)])
    assert workflow.get_ready() == [a, b]
    workflow.mark_running(a)
    workflow.mark_success(a)
    assert workflow.get_ready() == [b]
    workflow.mark_running(b)
    workflow.mark_success(b)
    assert workflow.get_ready() == [c]


def workflow_diamond_progression_test() -> None:
    print(f"[{__name__}] workflow_diamond_progression_test")
    a = _task("A")
    b = _task("B")
    c = _task("C")
    d = _task("D")
    workflow = Workflow(
        tasks=[a, b, c, d],
        edges=[(a, b), (a, c), (b, d), (c, d)],
    )
    assert workflow.get_ready() == [a]
    workflow.mark_running(a)
    workflow.mark_success(a)
    assert workflow.get_ready() == [b, c]
    workflow.mark_running(b)
    workflow.mark_success(b)
    assert workflow.get_ready() == [c]
    workflow.mark_running(c)
    workflow.mark_success(c)
    assert workflow.get_ready() == [d]
    workflow.mark_running(d)
    workflow.mark_success(d)
    assert workflow.get_ready() == []


def workflow_failure_in_diamond_blocks_final_test() -> None:
    print(f"[{__name__}] workflow_failure_in_diamond_blocks_final_test")
    a = _task("A")
    b = _task("B")
    c = _task("C")
    d = _task("D")
    workflow = Workflow(
        tasks=[a, b, c, d],
        edges=[(a, b), (a, c), (b, d), (c, d)],
    )
    workflow.mark_running(a)
    workflow.mark_success(a)
    workflow.mark_running(b)
    workflow.mark_failed(b)
    assert workflow.get_ready() == [c]
    workflow.mark_running(c)
    workflow.mark_success(c)
    assert workflow.get_ready() == []
