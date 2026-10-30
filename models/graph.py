from __future__ import annotations

from dataclasses import dataclass

from models.task import TaskID


@dataclass
class Node:
    task_id: TaskID


@dataclass
class Edge:
    source: TaskID
    target: TaskID


@dataclass
class Graph:
    nodes: list[Node]
    edges: list[Edge]