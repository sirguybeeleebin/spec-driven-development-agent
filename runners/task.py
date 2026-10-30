# runners/task.py

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from models import (
    AgentResult,
    AgentStatus,
    State,
    Task,
    TaskResult,
    TaskStatus,
    TestResult,
)


class TestRunner(Protocol):
    def test_function(self, state: State) -> str: ...
    def run(self, state: State) -> TestResult: ...


class Agent(Protocol):
    def run(self, *, state: State) -> AgentResult: ...


class TaskFSM(Protocol):
    @property
    def status(self) -> TaskStatus: ...
    def mark_running(self) -> None: ...
    def mark_success(self) -> None: ...
    def mark_error(self) -> None: ...


class TaskRunner:
    def __init__(
        self,
        *,
        researcher: Agent,
        implementer: Agent,
        tester: Agent,
        fixer: Agent,
        testrunner: TestRunner,
        max_fix_attempts: int,
        fsm: TaskFSM,
    ) -> None:
        self._researcher = researcher
        self._implementer = implementer
        self._tester = tester
        self._fixer = fixer
        self._testrunner = testrunner
        self._max_fix_attempts = max_fix_attempts
        self._fsm = fsm

    def run(self, task: Task) -> TaskResult:
        self._fsm.mark_running()

        state = State(
            goal=task.goal,
            target_file=task.target_file,
            target_test_file=task.target_test_file,
            declares=task.declares,
            interfaces=task.interfaces,
            constitution=task.constitution,
            sequence=task.sequence,
        )

        results: list[AgentResult] = []

        result = self._researcher.run(state=state)
        results.append(result)
        if result.status is not AgentStatus.SUCCESS:
            self._fsm.mark_error()
            return TaskResult(
                task_id=task.task_id,
                status=self._fsm.status,
                results=results,
            )
        state.researcher_summary = result.response

        result = self._implementer.run(state=state)
        results.append(result)
        if result.status is not AgentStatus.SUCCESS:
            self._fsm.mark_error()
            return TaskResult(
                task_id=task.task_id,
                status=self._fsm.status,
                results=results,
            )
        state.implementer_summary = result.response

        target_path = Path(state.target_file)
        if not target_path.exists():
            self._fsm.mark_error()
            return TaskResult(
                task_id=task.task_id,
                status=self._fsm.status,
                results=results,
            )

        failed_gherkins: list[str] = []

        for gherkin in task.gherkins:
            state.gherkin = gherkin
            state.target_declaration = gherkin.target_declaration
            state.test_function = self._testrunner.test_function(state)

            result = self._tester.run(state=state)
            results.append(result)
            if result.status is not AgentStatus.SUCCESS:
                self._fsm.mark_error()
                return TaskResult(
                    task_id=task.task_id,
                    status=self._fsm.status,
                    results=results,
                )
            state.tester_summary = result.response

            test_path = Path(state.target_test_file)
            if not test_path.exists():
                failed_gherkins.append(gherkin.name)
                continue

            test_result = self._testrunner.run(state)

            attempts = 0
            while not test_result.passed and attempts < self._max_fix_attempts:
                state.test_result = test_result

                result = self._fixer.run(state=state)
                results.append(result)
                if result.status is not AgentStatus.SUCCESS:
                    self._fsm.mark_error()
                    return TaskResult(
                        task_id=task.task_id,
                        status=self._fsm.status,
                        results=results,
                    )

                test_path = Path(state.target_test_file)
                if not test_path.exists():
                    break

                test_result = self._testrunner.run(state)
                attempts += 1

            if not test_result.passed:
                failed_gherkins.append(gherkin.name)
                continue

        self._fsm.mark_success()
        return TaskResult(
            task_id=task.task_id,
            status=self._fsm.status,
            results=results,
        )
