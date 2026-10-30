# fsms/agent_test.py

from __future__ import annotations

import pytest

from fsms.agent import AgentFSM
from models import AgentStatus

# ---- initial state ----


def test_initial_status_is_idle() -> None:
    assert AgentFSM().status is AgentStatus.IDLE


# ---- valid transitions ----


def test_idle_to_running() -> None:
    fsm = AgentFSM()
    fsm.mark_running()
    assert fsm.status is AgentStatus.RUNNING


def test_running_to_success() -> None:
    fsm = AgentFSM()
    fsm.mark_running()
    fsm.mark_success()
    assert fsm.status is AgentStatus.SUCCESS


def test_running_to_error() -> None:
    fsm = AgentFSM()
    fsm.mark_running()
    fsm.mark_error()
    assert fsm.status is AgentStatus.ERROR


def test_full_happy_path() -> None:
    fsm = AgentFSM()
    fsm.mark_running()
    fsm.mark_success()
    assert fsm.status is AgentStatus.SUCCESS


def test_full_error_path() -> None:
    fsm = AgentFSM()
    fsm.mark_running()
    fsm.mark_error()
    assert fsm.status is AgentStatus.ERROR


# ---- invalid transitions ----


def test_cannot_mark_running_from_running() -> None:
    fsm = AgentFSM()
    fsm.mark_running()
    with pytest.raises(ValueError, match="cannot mark_running from 'running'"):
        fsm.mark_running()


def test_cannot_mark_running_from_success() -> None:
    fsm = AgentFSM()
    fsm.mark_running()
    fsm.mark_success()
    with pytest.raises(ValueError, match="cannot mark_running from 'success'"):
        fsm.mark_running()


def test_cannot_mark_running_from_error() -> None:
    fsm = AgentFSM()
    fsm.mark_running()
    fsm.mark_error()
    with pytest.raises(ValueError, match="cannot mark_running from 'error'"):
        fsm.mark_running()


def test_cannot_mark_success_from_idle() -> None:
    fsm = AgentFSM()
    with pytest.raises(ValueError, match="cannot mark_success from 'idle'"):
        fsm.mark_success()


def test_cannot_mark_success_from_success() -> None:
    fsm = AgentFSM()
    fsm.mark_running()
    fsm.mark_success()
    with pytest.raises(ValueError, match="cannot mark_success from 'success'"):
        fsm.mark_success()


def test_cannot_mark_success_from_error() -> None:
    fsm = AgentFSM()
    fsm.mark_running()
    fsm.mark_error()
    with pytest.raises(ValueError, match="cannot mark_success from 'error'"):
        fsm.mark_success()


def test_cannot_mark_error_from_idle() -> None:
    fsm = AgentFSM()
    with pytest.raises(ValueError, match="cannot mark_error from 'idle'"):
        fsm.mark_error()


def test_cannot_mark_error_from_success() -> None:
    fsm = AgentFSM()
    fsm.mark_running()
    fsm.mark_success()
    with pytest.raises(ValueError, match="cannot mark_error from 'success'"):
        fsm.mark_error()


def test_cannot_mark_error_from_error() -> None:
    fsm = AgentFSM()
    fsm.mark_running()
    fsm.mark_error()
    with pytest.raises(ValueError, match="cannot mark_error from 'error'"):
        fsm.mark_error()


# ---- state is preserved after failed transition ----


def test_failed_transition_preserves_state() -> None:
    fsm = AgentFSM()
    with pytest.raises(ValueError):
        fsm.mark_success()
    assert fsm.status is AgentStatus.IDLE
