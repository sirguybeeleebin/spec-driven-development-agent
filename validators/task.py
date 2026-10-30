# validators/task.py

from __future__ import annotations

import re

from models import Task

_TASK_ID = re.compile(r"^\d+_[a-z0-9_]+$")
_ACTIVITY_HEAD = re.compile(r"^(flowchart|graph)\s")
_SEQUENCE_HEAD = re.compile(r"^sequenceDiagram\b")


def validate_task(task: Task) -> None:
    if not _TASK_ID.match(task.task_id):
        raise ValueError(f"task: bad task_id: {task.task_id!r}")
    if not task.goal:
        raise ValueError("task: empty goal")
    if not task.target:
        raise ValueError("task: empty target")
    if not task.target_test:
        raise ValueError("task: empty target_test")
    if task.target == task.target_test:
        raise ValueError("task: target and target_test must differ")
    if not task.interfaces:
        raise ValueError("task: no interfaces")
    if not task.scenarios:
        raise ValueError("task: no scenarios")

    interface_names: set[str] = set()
    for interface in task.interfaces:
        if not interface.name:
            raise ValueError("task: interface with empty name")
        if interface.name in interface_names:
            raise ValueError(f"task: duplicate interface {interface.name!r}")
        interface_names.add(interface.name)

    scenario_names: set[str] = set()
    for scenario in task.scenarios:
        if not scenario.name:
            raise ValueError("task: scenario with empty name")
        if scenario.name in scenario_names:
            raise ValueError(f"task: duplicate scenario {scenario.name!r}")
        scenario_names.add(scenario.name)
        if not scenario.given:
            raise ValueError(f"task: scenario {scenario.name!r} missing given")
        if not scenario.when:
            raise ValueError(f"task: scenario {scenario.name!r} missing when")
        if not scenario.then:
            raise ValueError(f"task: scenario {scenario.name!r} missing then")

    if task.activity is not None:
        activity = task.activity.strip()
        if not activity:
            raise ValueError("task: empty activity")
        if not _ACTIVITY_HEAD.match(activity):
            raise ValueError(
                "task: activity must start with 'flowchart <DIR>' or "
                f"'graph <DIR>', got: {activity[:40]!r}"
            )

    if task.sequence is not None:
        sequence = task.sequence.strip()
        if not sequence:
            raise ValueError("task: empty sequence")
        if not _SEQUENCE_HEAD.match(sequence):
            raise ValueError(
                "task: sequence must start with 'sequenceDiagram', "
                f"got: {sequence[:40]!r}"
            )