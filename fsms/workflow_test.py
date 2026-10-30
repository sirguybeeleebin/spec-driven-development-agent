# fsms/workflow_test.py

from __future__ import annotations

import pytest

from fsms.workflow import WorkflowFSM
from models import WorkflowStatus

# ---- initial state ----


def test_default_initial_status_is_idle() -> None:
    assert WorkflowFSM().status is WorkflowStatus.IDLE


@pytest.mark.parametrize(
    "initial",
    [
        WorkflowStatus.IDLE,
        WorkflowStatus.HOLD,
        WorkflowStatus.RUNNING,
        WorkflowStatus.SUCCESS,
        WorkflowStatus.ERROR,
    ],
)
def test_constructor_accepts_any_status(initial: WorkflowStatus) -> None:
    assert WorkflowFSM(initial).status is initial


# ---- IDLE transitions ----


def test_idle_to_hold() -> None:
    fsm = WorkflowFSM()
    fsm.mark_hold()
    assert fsm.status is WorkflowStatus.HOLD


def test_idle_to_running() -> None:
    fsm = WorkflowFSM()
    fsm.mark_running()
    assert fsm.status is WorkflowStatus.RUNNING


def test_idle_cannot_mark_success() -> None:
    fsm = WorkflowFSM()
    with pytest.raises(ValueError, match="cannot mark_success from 'idle'"):
        fsm.mark_success()


def test_idle_cannot_mark_error() -> None:
    fsm = WorkflowFSM()
    with pytest.raises(ValueError, match="cannot mark_error from 'idle'"):
        fsm.mark_error()


def test_idle_cannot_mark_failed() -> None:
    fsm = WorkflowFSM()
    with pytest.raises(ValueError, match="cannot mark_failed from 'idle'"):
        fsm.mark_failed()


# ---- HOLD transitions ----


def test_hold_to_running() -> None:
    fsm = WorkflowFSM(WorkflowStatus.HOLD)
    fsm.mark_running()
    assert fsm.status is WorkflowStatus.RUNNING


def test_hold_to_error_via_mark_failed() -> None:
    fsm = WorkflowFSM(WorkflowStatus.HOLD)
    fsm.mark_failed()
    assert fsm.status is WorkflowStatus.ERROR


def test_hold_cannot_mark_hold() -> None:
    fsm = WorkflowFSM(WorkflowStatus.HOLD)
    with pytest.raises(ValueError, match="cannot mark_hold from 'hold'"):
        fsm.mark_hold()


def test_hold_cannot_mark_success() -> None:
    fsm = WorkflowFSM(WorkflowStatus.HOLD)
    with pytest.raises(ValueError, match="cannot mark_success from 'hold'"):
        fsm.mark_success()


def test_hold_cannot_mark_error() -> None:
    # HOLD → ERROR is only allowed via mark_failed, not mark_error.
    fsm = WorkflowFSM(WorkflowStatus.HOLD)
    with pytest.raises(ValueError, match="cannot mark_error from 'hold'"):
        fsm.mark_error()


# ---- RUNNING transitions ----


def test_running_to_success() -> None:
    fsm = WorkflowFSM(WorkflowStatus.RUNNING)
    fsm.mark_success()
    assert fsm.status is WorkflowStatus.SUCCESS


def test_running_to_error() -> None:
    fsm = WorkflowFSM(WorkflowStatus.RUNNING)
    fsm.mark_error()
    assert fsm.status is WorkflowStatus.ERROR


def test_running_cannot_mark_hold() -> None:
    fsm = WorkflowFSM(WorkflowStatus.RUNNING)
    with pytest.raises(ValueError, match="cannot mark_hold from 'running'"):
        fsm.mark_hold()


def test_running_cannot_mark_running() -> None:
    fsm = WorkflowFSM(WorkflowStatus.RUNNING)
    with pytest.raises(ValueError, match="cannot mark_running from 'running'"):
        fsm.mark_running()


def test_running_cannot_mark_failed() -> None:
    fsm = WorkflowFSM(WorkflowStatus.RUNNING)
    with pytest.raises(ValueError, match="cannot mark_failed from 'running'"):
        fsm.mark_failed()


# ---- terminal states ----


def test_success_is_terminal() -> None:
    fsm = WorkflowFSM(WorkflowStatus.SUCCESS)
    for method in (
        fsm.mark_hold,
        fsm.mark_running,
        fsm.mark_success,
        fsm.mark_error,
        fsm.mark_failed,
    ):
        with pytest.raises(ValueError, match="from 'success'"):
            method()
    assert fsm.status is WorkflowStatus.SUCCESS


def test_error_is_terminal() -> None:
    fsm = WorkflowFSM(WorkflowStatus.ERROR)
    for method in (
        fsm.mark_hold,
        fsm.mark_running,
        fsm.mark_success,
        fsm.mark_error,
        fsm.mark_failed,
    ):
        with pytest.raises(ValueError, match="from 'error'"):
            method()
    assert fsm.status is WorkflowStatus.ERROR


# ---- complete paths ----


def test_path_idle_hold_running_success() -> None:
    fsm = WorkflowFSM()
    fsm.mark_hold()
    fsm.mark_running()
    fsm.mark_success()
    assert fsm.status is WorkflowStatus.SUCCESS


def test_path_idle_hold_running_error() -> None:
    fsm = WorkflowFSM()
    fsm.mark_hold()
    fsm.mark_running()
    fsm.mark_error()
    assert fsm.status is WorkflowStatus.ERROR


def test_path_idle_hold_failed() -> None:
    fsm = WorkflowFSM()
    fsm.mark_hold()
    fsm.mark_failed()
    assert fsm.status is WorkflowStatus.ERROR


def test_path_idle_running_success() -> None:
    fsm = WorkflowFSM()
    fsm.mark_running()
    fsm.mark_success()
    assert fsm.status is WorkflowStatus.SUCCESS


def test_path_idle_running_error() -> None:
    fsm = WorkflowFSM()
    fsm.mark_running()
    fsm.mark_error()
    assert fsm.status is WorkflowStatus.ERROR


# ---- state is preserved after failed transition ----


def test_failed_transition_preserves_state() -> None:
    fsm = WorkflowFSM()
    with pytest.raises(ValueError):
        fsm.mark_success()
    assert fsm.status is WorkflowStatus.IDLE
