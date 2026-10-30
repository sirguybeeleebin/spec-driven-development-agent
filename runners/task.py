from __future__ import annotations

from pathlib import Path
from typing import Protocol

from models import (
    AgentStatus,
    State,
    Task,
    TaskResult,
    TaskStatus,
    TestResult,
)


class RepoMap(Protocol):
    def render(self, state: State) -> str: ...


class TestRunner(Protocol):
    def test_function(self, state: State) -> str: ...
    def run(self, state: State) -> TestResult: ...


class Agent(Protocol):
    def run(self, state: State) -> State: ...


class TaskRunner:
    def __init__(
        self,
        *,
        repomap: RepoMap,
        researcher: Agent,
        implementer: Agent,
        tester: Agent,
        fixer: Agent,
        testrunner: TestRunner,
        max_fix_attempts: int,
    ) -> None:
        self._repomap = repomap
        self._researcher = researcher
        self._implementer = implementer
        self._tester = tester
        self._fixer = fixer
        self._testrunner = testrunner
        self._max_fix_attempts = max_fix_attempts

    def run(self, task: Task) -> TaskResult:
        state: State = {
            "task_id": task.task_id,
            "goal": task.goal,
            "target": task.target,
            "target_test": task.target_test,
            "constitution": task.constitution,
            "interfaces": task.interfaces,
            "scenarios": task.scenarios,
        }
        if task.activity is not None:
            state["activity"] = task.activity
        if task.sequence is not None:
            state["sequence"] = task.sequence
        state["context_map"] = self._repomap.render(state)

        print(
            f"[task_runner] init task_id={state['task_id']} "
            f"target={state['target']} "
            f"target_test={state['target_test']} "
            f"interfaces={[i.name for i in state['interfaces']]} "
            f"scenarios={[s.name for s in state['scenarios']]} "
            f"context_map_len={len(state['context_map'])}"
        )

        states: list[State] = []

        print("[task_runner] phase=researcher start")
        state = self._researcher.run(state)
        states.append(state.copy())
        state["context_map"] = self._repomap.render(state)
        print(
            f"[task_runner] phase=researcher end status={state['status']} "
            f"researcher_response_len={len(state['researcher']['response'])} "
            f"researcher_history={len(state['researcher']['history'])} "
            f"researcher_metrics={len(state['researcher']['metrics'])} "
            f"context_map_len={len(state['context_map'])}"
        )
        if state["status"] is not AgentStatus.DONE:
            return TaskResult(
                task_id=state["task_id"],
                states=states,
                status=TaskStatus.FAILED,
            )

        print("[task_runner] phase=implementer start")
        state = self._implementer.run(state)
        states.append(state.copy())
        state["context_map"] = self._repomap.render(state)
        print(
            f"[task_runner] phase=implementer end status={state['status']} "
            f"implementer_response_len="
            f"{len(state['implementer']['response'])} "
            f"implementer_history="
            f"{len(state['implementer']['history'])} "
            f"implementer_metrics="
            f"{len(state['implementer']['metrics'])} "
            f"context_map_len={len(state['context_map'])}"
        )
        if state["status"] is not AgentStatus.DONE:
            return TaskResult(
                task_id=state["task_id"],
                states=states,
                status=TaskStatus.FAILED,
            )

        target_path = Path(state["target"])
        if not target_path.exists():
            print(
                f"[task_runner] implementer finished DONE but "
                f"{state['target']} was not created"
            )
            return TaskResult(
                task_id=state["task_id"],
                states=states,
                status=TaskStatus.FAILED,
            )

        total = len(state["scenarios"])
        for index, scenario in enumerate(state["scenarios"], start=1):
            print(
                f"[task_runner] scenario {index}/{total} "
                f"name={scenario.name!r} start"
            )
            state["scenario"] = scenario
            state["test_function"] = self._testrunner.test_function(state)
            print(f"[task_runner] test_function={state['test_function']!r}")

            print("[task_runner] phase=tester start")
            state = self._tester.run(state)
            states.append(state.copy())
            state["context_map"] = self._repomap.render(state)
            print(
                f"[task_runner] phase=tester end status={state['status']} "
                f"tester_response_len={len(state['tester']['response'])} "
                f"tester_history={len(state['tester']['history'])} "
                f"tester_metrics={len(state['tester']['metrics'])} "
                f"context_map_len={len(state['context_map'])}"
            )
            if state["status"] is not AgentStatus.DONE:
                return TaskResult(
                    task_id=state["task_id"],
                    states=states,
                    status=TaskStatus.FAILED,
                )

            test_path = Path(state["target_test"])
            if not test_path.exists():
                print(
                    f"[task_runner] tester finished DONE but "
                    f"{state['target_test']} was not created"
                )
                return TaskResult(
                    task_id=state["task_id"],
                    states=states,
                    status=TaskStatus.FAILED,
                )
            state["test_source"] = test_path.read_text(encoding="utf-8")
            print(
                f"[task_runner] test_source refreshed after tester "
                f"len={len(state['test_source'])}"
            )

            if f"def {state['test_function']}(" not in state["test_source"]:
                print(
                    f"[task_runner] {state['target_test']} does not "
                    f"contain def {state['test_function']}"
                )
                return TaskResult(
                    task_id=state["task_id"],
                    states=states,
                    status=TaskStatus.FAILED,
                )

            test_result = self._testrunner.run(state)
            print(
                f"[task_runner] test passed={test_result.passed} "
                f"output_len={len(test_result.output or '')}"
            )

            attempts = 0
            while not test_result.passed and attempts < self._max_fix_attempts:
                print(
                    f"[task_runner] phase=fixer start "
                    f"attempt={attempts + 1}/{self._max_fix_attempts}"
                )
                state["test_output"] = test_result.output
                state = self._fixer.run(state)
                states.append(state.copy())
                state["context_map"] = self._repomap.render(state)
                print(
                    f"[task_runner] phase=fixer end status={state['status']} "
                    f"fixer_response_len={len(state['fixer']['response'])} "
                    f"fixer_history={len(state['fixer']['history'])} "
                    f"fixer_metrics={len(state['fixer']['metrics'])} "
                    f"context_map_len={len(state['context_map'])}"
                )
                if state["status"] is not AgentStatus.DONE:
                    return TaskResult(
                        task_id=state["task_id"],
                        states=states,
                        status=TaskStatus.FAILED,
                    )

                test_path = Path(state["target_test"])
                if not test_path.exists():
                    print(
                        f"[task_runner] fixer finished DONE but "
                        f"{state['target_test']} does not exist"
                    )
                    return TaskResult(
                        task_id=state["task_id"],
                        states=states,
                        status=TaskStatus.FAILED,
                    )
                state["test_source"] = test_path.read_text(encoding="utf-8")
                print(
                    f"[task_runner] test_source refreshed after fixer "
                    f"len={len(state['test_source'])}"
                )

                if f"def {state['test_function']}(" not in state["test_source"]:
                    print(
                        f"[task_runner] {state['target_test']} does not "
                        f"contain def {state['test_function']} after fixer"
                    )
                    return TaskResult(
                        task_id=state["task_id"],
                        states=states,
                        status=TaskStatus.FAILED,
                    )

                test_result = self._testrunner.run(state)
                print(
                    f"[task_runner] test passed={test_result.passed} "
                    f"output_len={len(test_result.output or '')}"
                )
                attempts += 1

            if not test_result.passed:
                print(
                    f"[task_runner] scenario {scenario.name!r} unresolved "
                    f"after {attempts} attempt(s)"
                )
                return TaskResult(
                    task_id=state["task_id"],
                    states=states,
                    status=TaskStatus.FAILED,
                )

            print(
                f"[task_runner] scenario {index}/{total} "
                f"name={scenario.name!r} passed"
            )

        print("[task_runner] all scenarios passed -> DONE")
        return TaskResult(
            task_id=state["task_id"],
            states=states,
            status=TaskStatus.DONE,
        )