# scheduler/scheduler.py

from __future__ import annotations

from fsms import WorkflowFSM
from models import Task, TaskID, Workflow, WorkflowStatus


class Scheduler:
    """Determines which tasks are ready to run in a workflow.

    A task is ready when its workflow status is IDLE or HOLD and every
    ancestor is SUCCESS. IDLE tasks that are not yet ready transition
    to HOLD.
    """

    def get_ready_tasks(self, workflow: Workflow) -> list[Task]:
        ancestors: dict[TaskID, list[TaskID]] = {
            task.task_id: [] for task in workflow.tasks
        }
        for edge in workflow.graph.edges:
            ancestors[edge.target.task_id].append(edge.source.task_id)

        ready: list[Task] = []
        for task in workflow.tasks:
            status = workflow.statuses[task.task_id]
            if status not in (WorkflowStatus.IDLE, WorkflowStatus.HOLD):
                continue

            if all(
                workflow.statuses[aid] is WorkflowStatus.SUCCESS
                for aid in ancestors[task.task_id]
            ):
                ready.append(task)
            elif status is WorkflowStatus.IDLE:
                fsm = WorkflowFSM(status)
                fsm.mark_hold()
                workflow.statuses[task.task_id] = fsm.status

        return ready
