from __future__ import annotations

from dataclasses import dataclass, field

from models.task import TaskID


@dataclass(frozen=True)
class Node:
    task_id: TaskID


@dataclass(frozen=True)
class Edge:
    source: Node
    target: Node


@dataclass
class Graph:
    nodes: list[Node]
    edges: list[Edge] = field(default_factory=list)
