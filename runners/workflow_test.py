# runners/workflow_test.py

from __future__ import annotations

from models import (
    AgentResult,
    AgentStatus,
    Message,
    Role,
    Task,
    TaskID,
    TaskResult,
    TaskStatus,
    WorkflowResult,
)
from runners.workflow import WorkflowRunner


class FakeWorkflow:
    def __init__(self, batches: list[list[Task]]) -> None:
        self._batches = list(batches)
        self._cursor = 0
        self.ready_calls = 0
        self.events: list[tuple[str, str]] = []

    def get_ready(self) -> list[Task]:
        self.ready_calls += 1
        if self._cursor >= len(self._batches):
            return []
        batch = self._batches[self._cursor]
        self._cursor += 1
        return batch

    def mark_running(self, task: Task) -> None:
        self.events.append(("running", task.task_id))

    def mark_success(self, task: Task) -> None:
        self.events.append(("success", task.task_id))

    def mark_failed(self, task: Task) -> None:
        self.events.append(("failed", task.task_id))


class FakeTaskRunner:
    def __init__(
        self,
        results: list[TaskResult] | None = None,
        raise_on: set[str] | None = None,
    ) -> None:
        self._results = list(results or [])
        self._raise_on = raise_on or set()
        self.calls: list[Task] = []

    def run(self, task: Task) -> TaskResult:
        self.calls.append(task)
        if task.task_id in self._raise_on:
            raise RuntimeError(f"boom on {task.task_id}")
        if not self._results:
            raise AssertionError(
                f"unexpected run() call for task {task.task_id!r}: "
                f"no scripted result left"
            )
        return self._results.pop(0)


def _task(task_id: str) -> Task:
    return Task(
        task_id=TaskID(task_id),
        goal=f"goal for {task_id}",
        target=f"src/{task_id}.py",
        target_test=f"tests/test_{task_id}.py",
        interfaces=[],
        scenarios=[],
    )


def _task_result(
    task: Task,
    status: TaskStatus = TaskStatus.DONE,
    agent_status: AgentStatus = AgentStatus.DONE,
) -> TaskResult:
    return TaskResult(
        task_id=task.task_id,
        results=[
            AgentResult(
                status=agent_status,
                messages=[Message(role=Role.ASSISTANT, content="done")],
                metrics=[],
            )
        ],
        status=status,
    )


def workflow_runner_empty_workflow_test() -> None:
    print(f"[{__name__}] workflow_runner_empty_workflow_test")
    workflow = FakeWorkflow(batches=[])
    task_runner = FakeTaskRunner()
    runner = WorkflowRunner(task_runner)

    result = runner.run(workflow)

    assert isinstance(result, WorkflowResult)
    assert result.results == []
    assert result.statuses == []
    assert workflow.events == []
    assert task_runner.calls == []
    assert workflow.ready_calls == 1


def workflow_runner_single_task_done_test() -> None:
    print(f"[{__name__}] workflow_runner_single_task_done_test")
    t1 = _task("t1")
    workflow = FakeWorkflow(batches=[[t1]])
    task_runner = FakeTaskRunner([_task_result(t1, TaskStatus.DONE)])
    runner = WorkflowRunner(task_runner)

    result = runner.run(workflow)

    assert len(result.results) == 1
    assert result.results[0].task_id == "t1"
    assert result.statuses == [TaskStatus.DONE]
    assert result.ok is True
    assert workflow.events == [
        ("running", "t1"),
        ("success", "t1"),
    ]
    assert task_runner.calls == [t1]


def workflow_runner_multiple_tasks_in_one_batch_test() -> None:
    print(f"[{__name__}] workflow_runner_multiple_tasks_in_one_batch_test")
    t1 = _task("t1")
    t2 = _task("t2")
    workflow = FakeWorkflow(batches=[[t1, t2]])
    task_runner = FakeTaskRunner(
        [
            _task_result(t1, TaskStatus.DONE),
            _task_result(t2, TaskStatus.DONE),
        ]
    )
    runner = WorkflowRunner(task_runner)

    result = runner.run(workflow)

    assert len(result.results) == 2
    assert result.statuses == [TaskStatus.DONE, TaskStatus.DONE]
    assert result.ok is True
    assert workflow.events == [
        ("running", "t1"),
        ("success", "t1"),
        ("running", "t2"),
        ("success", "t2"),
    ]


def workflow_runner_multiple_batches_test() -> None:
    print(f"[{__name__}] workflow_runner_multiple_batches_test")
    t1 = _task("t1")
    t2 = _task("t2")
    t3 = _task("t3")
    workflow = FakeWorkflow(batches=[[t1], [t2, t3]])
    task_runner = FakeTaskRunner(
        [
            _task_result(t1, TaskStatus.DONE),
            _task_result(t2, TaskStatus.DONE),
            _task_result(t3, TaskStatus.DONE),
        ]
    )
    runner = WorkflowRunner(task_runner)

    result = runner.run(workflow)

    assert [r.task_id for r in result.results] == ["t1", "t2", "t3"]
    assert result.statuses == [TaskStatus.DONE] * 3


def workflow_runner_failed_task_is_marked_failed_test() -> None:
    print(f"[{__name__}] workflow_runner_failed_task_is_marked_failed_test")
    t1 = _task("t1")
    workflow = FakeWorkflow(batches=[[t1]])
    task_runner = FakeTaskRunner([_task_result(t1, TaskStatus.FAILED)])
    runner = WorkflowRunner(task_runner)

    result = runner.run(workflow)

    assert result.statuses == [TaskStatus.FAILED]
    assert result.ok is False
    assert workflow.events == [
        ("running", "t1"),
        ("failed", "t1"),
    ]


def workflow_runner_failure_does_not_stop_other_tasks_test() -> None:
    print(f"[{__name__}] workflow_runner_failure_does_not_stop_other_tasks_test")
    t1 = _task("t1")
    t2 = _task("t2")
    workflow = FakeWorkflow(batches=[[t1, t2]])
    task_runner = FakeTaskRunner(
        [
            _task_result(t1, TaskStatus.FAILED),
            _task_result(t2, TaskStatus.DONE),
        ]
    )
    runner = WorkflowRunner(task_runner)

    result = runner.run(workflow)

    assert result.statuses == [TaskStatus.FAILED, TaskStatus.DONE]
    assert result.ok is False
    assert workflow.events == [
        ("running", "t1"),
        ("failed", "t1"),
        ("running", "t2"),
        ("success", "t2"),
    ]


def workflow_runner_exception_is_caught_and_marks_failed_test() -> None:
    print(f"[{__name__}] workflow_runner_exception_is_caught_and_marks_failed_test")
    t1 = _task("t1")
    workflow = FakeWorkflow(batches=[[t1]])
    task_runner = FakeTaskRunner(raise_on={"t1"})
    runner = WorkflowRunner(task_runner)

    result = runner.run(workflow)

    assert len(result.results) == 1
    synthetic = result.results[0]
    assert synthetic.task_id == "t1"
    assert synthetic.status is TaskStatus.FAILED
    assert synthetic.results == []
    assert workflow.events == [
        ("running", "t1"),
        ("failed", "t1"),
    ]


def workflow_runner_exception_does_not_stop_other_tasks_test() -> None:
    print(f"[{__name__}] workflow_runner_exception_does_not_stop_other_tasks_test")
    t1 = _task("t1")
    t2 = _task("t2")
    workflow = FakeWorkflow(batches=[[t1, t2]])
    task_runner = FakeTaskRunner(
        results=[_task_result(t2, TaskStatus.DONE)],
        raise_on={"t1"},
    )
    runner = WorkflowRunner(task_runner)

    result = runner.run(workflow)

    assert len(result.results) == 2
    assert result.results[0].task_id == "t1"
    assert result.results[0].status is TaskStatus.FAILED
    assert result.results[1].task_id == "t2"
    assert result.results[1].status is TaskStatus.DONE
    assert result.statuses == [TaskStatus.FAILED, TaskStatus.DONE]
    assert [t.task_id for t in task_runner.calls] == ["t1", "t2"]


def workflow_runner_results_and_statuses_aligned_test() -> None:
    print(f"[{__name__}] workflow_runner_results_and_statuses_aligned_test")
    tasks = [_task(f"t{i}") for i in range(4)]
    workflow = FakeWorkflow(batches=[tasks])
    task_runner = FakeTaskRunner(
        [
            _task_result(tasks[0], TaskStatus.DONE),
            _task_result(tasks[1], TaskStatus.FAILED),
            _task_result(tasks[2], TaskStatus.DONE),
            _task_result(tasks[3], TaskStatus.FAILED),
        ]
    )
    runner = WorkflowRunner(task_runner)

    result = runner.run(workflow)

    assert len(result.results) == len(result.statuses) == 4
    for task_result, status in zip(result.results, result.statuses, strict=True):
        assert task_result.status is status


def workflow_runner_task_ids_preserved_test() -> None:
    print(f"[{__name__}] workflow_runner_task_ids_preserved_test")
    t1 = _task("alpha")
    t2 = _task("beta")
    workflow = FakeWorkflow(batches=[[t1, t2]])
    task_runner = FakeTaskRunner(
        [
            _task_result(t1, TaskStatus.DONE),
            _task_result(t2, TaskStatus.DONE),
        ]
    )
    runner = WorkflowRunner(task_runner)

    result = runner.run(workflow)

    assert [r.task_id for r in result.results] == ["alpha", "beta"]


def workflow_runner_marks_running_before_run_test() -> None:
    print(f"[{__name__}] workflow_runner_marks_running_before_run_test")
    t1 = _task("t1")
    workflow = FakeWorkflow(batches=[[t1]])
    task_runner = FakeTaskRunner([_task_result(t1)])
    runner = WorkflowRunner(task_runner)

    runner.run(workflow)

    assert workflow.events[0] == ("running", "t1")
    assert workflow.events[-1] == ("success", "t1")


def workflow_runner_marks_success_only_on_done_test() -> None:
    print(f"[{__name__}] workflow_runner_marks_success_only_on_done_test")
    t1 = _task("t1")
    t2 = _task("t2")
    workflow = FakeWorkflow(batches=[[t1, t2]])
    task_runner = FakeTaskRunner(
        [
            _task_result(t1, TaskStatus.DONE),
            _task_result(t2, TaskStatus.FAILED),
        ]
    )
    runner = WorkflowRunner(task_runner)

    runner.run(workflow)

    assert ("success", "t1") in workflow.events
    assert ("failed", "t1") not in workflow.events
    assert ("failed", "t2") in workflow.events
    assert ("success", "t2") not in workflow.events


def workflow_runner_stops_on_empty_get_ready_test() -> None:
    print(f"[{__name__}] workflow_runner_stops_on_empty_get_ready_test")
    t1 = _task("t1")
    workflow = FakeWorkflow(batches=[[t1]])
    task_runner = FakeTaskRunner([_task_result(t1)])
    runner = WorkflowRunner(task_runner)

    runner.run(workflow)

    assert len(task_runner.calls) == 1
    assert workflow.ready_calls == 2
    assert workflow.events == [
        ("running", "t1"),
        ("success", "t1"),
    ]


def workflow_runner_handles_empty_on_first_call_test() -> None:
    print(f"[{__name__}] workflow_runner_handles_empty_on_first_call_test")
    workflow = FakeWorkflow(batches=[])
    task_runner = FakeTaskRunner()
    runner = WorkflowRunner(task_runner)

    result = runner.run(workflow)

    assert result.results == []
    assert task_runner.calls == []
    assert workflow.ready_calls == 1
