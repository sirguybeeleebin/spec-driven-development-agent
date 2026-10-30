# validators/graph_test.py

from __future__ import annotations

import pytest

from models import Edge, Graph, Node
from validators import validate_graph


def _graph(
    nodes: list[str] | None = None,
    edges: list[tuple[str, str]] | None = None,
) -> Graph:
    if nodes is None:
        nodes = ["t1", "t2"]
    if edges is None:
        edges = []
    return Graph(
        nodes=[Node(task_id=n) for n in nodes],
        edges=[Edge(source=s, target=t) for s, t in edges],
    )


def validate_graph_accepts_valid_graph_test() -> None:
    print(f"[{__name__}] validate_graph_accepts_valid_graph_test")
    validate_graph(_graph(["t1", "t2"], [("t1", "t2")]))


def validate_graph_accepts_standalone_nodes_test() -> None:
    print(f"[{__name__}] validate_graph_accepts_standalone_nodes_test")
    validate_graph(_graph(["a", "b", "c"], []))


def validate_graph_no_nodes_raises_test() -> None:
    print(f"[{__name__}] validate_graph_no_nodes_raises_test")
    with pytest.raises(ValueError, match="no nodes"):
        validate_graph(_graph([], []))


def validate_graph_empty_node_id_raises_test() -> None:
    print(f"[{__name__}] validate_graph_empty_node_id_raises_test")
    with pytest.raises(ValueError, match="empty task_id"):
        validate_graph(_graph(["", "t2"], []))


def validate_graph_duplicate_node_raises_test() -> None:
    print(f"[{__name__}] validate_graph_duplicate_node_raises_test")
    with pytest.raises(ValueError, match="duplicate node"):
        validate_graph(_graph(["t1", "t1"], []))


def validate_graph_edge_source_not_node_raises_test() -> None:
    print(f"[{__name__}] validate_graph_edge_source_not_node_raises_test")
    with pytest.raises(ValueError, match="edge source"):
        validate_graph(_graph(["t1"], [("missing", "t1")]))


def validate_graph_edge_target_not_node_raises_test() -> None:
    print(f"[{__name__}] validate_graph_edge_target_not_node_raises_test")
    with pytest.raises(ValueError, match="edge target"):
        validate_graph(_graph(["t1"], [("t1", "missing")]))
