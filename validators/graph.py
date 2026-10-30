# validators/graph.py

from __future__ import annotations

from models import Graph


def validate_graph(graph: Graph) -> None:
    if not graph.nodes:
        raise ValueError("graph: no nodes")

    node_ids: set[str] = set()
    for node in graph.nodes:
        if not node.task_id:
            raise ValueError("graph: node with empty task_id")
        if node.task_id in node_ids:
            raise ValueError(f"graph: duplicate node {node.task_id!r}")
        node_ids.add(node.task_id)

    for edge in graph.edges:
        if edge.source not in node_ids:
            raise ValueError(f"graph: edge source {edge.source!r} is not a node")
        if edge.target not in node_ids:
            raise ValueError(f"graph: edge target {edge.target!r} is not a node")
