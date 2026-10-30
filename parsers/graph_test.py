# parsers/graph_test.py

from __future__ import annotations

import pytest

from parsers import parse_graph


def _fence(body: str) -> str:
    return f"```mermaid\n{body}\n```\n"


def parse_graph_parses_chain_test() -> None:
    print(f"[{__name__}] parse_graph_parses_chain_test")
    workflow = _fence("graph LR\nt1 --> t2\nt2 --> t3\nt3")
    graph = parse_graph(workflow)

    assert [n.task_id for n in graph.nodes] == ["t1", "t2", "t3"]
    assert [(e.source, e.target) for e in graph.edges] == [
        ("t1", "t2"),
        ("t2", "t3"),
    ]


def parse_graph_preserves_declaration_order_test() -> None:
    print(f"[{__name__}] parse_graph_preserves_declaration_order_test")
    workflow = _fence("graph TD\nb\na\nc")
    graph = parse_graph(workflow)

    assert [n.task_id for n in graph.nodes] == ["b", "a", "c"]


def parse_graph_handles_standalone_nodes_test() -> None:
    print(f"[{__name__}] parse_graph_handles_standalone_nodes_test")
    workflow = _fence("graph LR\nt1\nt2")
    graph = parse_graph(workflow)

    assert [n.task_id for n in graph.nodes] == ["t1", "t2"]
    assert graph.edges == []


def parse_graph_handles_multiple_edges_per_line_test() -> None:
    print(f"[{__name__}] parse_graph_handles_multiple_edges_per_line_test")
    workflow = _fence("graph LR\nt1 --> t2 --> t3")
    graph = parse_graph(workflow)

    assert [n.task_id for n in graph.nodes] == ["t1", "t2", "t3"]
    assert [(e.source, e.target) for e in graph.edges] == [
        ("t1", "t2"),
        ("t2", "t3"),
    ]


def parse_graph_dedupes_nodes_test() -> None:
    print(f"[{__name__}] parse_graph_dedupes_nodes_test")
    workflow = _fence("graph LR\nt1 --> t2\nt1 --> t3")
    graph = parse_graph(workflow)

    assert [n.task_id for n in graph.nodes] == ["t1", "t2", "t3"]


def parse_graph_self_loop_test() -> None:
    print(f"[{__name__}] parse_graph_self_loop_test")
    workflow = _fence("graph LR\nt1 --> t1")
    graph = parse_graph(workflow)

    assert [n.task_id for n in graph.nodes] == ["t1"]
    assert [(e.source, e.target) for e in graph.edges] == [("t1", "t1")]


def parse_graph_ignores_blank_lines_test() -> None:
    print(f"[{__name__}] parse_graph_ignores_blank_lines_test")
    workflow = _fence("graph LR\n\nt1\n\nt2\n")
    graph = parse_graph(workflow)

    assert [n.task_id for n in graph.nodes] == ["t1", "t2"]


def parse_graph_ignores_surrounding_prose_test() -> None:
    print(f"[{__name__}] parse_graph_ignores_surrounding_prose_test")
    workflow = (
        "# Workflow\n\n"
        "This is the shop workflow.\n\n"
        "```mermaid\n"
        "graph LR\n"
        "t1 --> t2\n"
        "```\n\n"
        "Some trailing notes.\n"
    )
    graph = parse_graph(workflow)

    assert [n.task_id for n in graph.nodes] == ["t1", "t2"]


@pytest.mark.parametrize("direction", ["LR", "RL", "TD", "TB", "BT"])
def parse_graph_accepts_all_directions_test(
    direction: str,
) -> None:
    print(f"[{__name__}] parse_graph_accepts_all_directions_test {direction}")
    workflow = _fence(f"graph {direction}\nt1")
    graph = parse_graph(workflow)

    assert [n.task_id for n in graph.nodes] == ["t1"]


@pytest.mark.parametrize("direction", ["lr", "Rl", "tD", "tb", "Bt"])
def parse_graph_direction_case_insensitive_test(
    direction: str,
) -> None:
    print(f"[{__name__}] parse_graph_direction_case_insensitive_test {direction}")
    workflow = _fence(f"graph {direction}\nt1")
    graph = parse_graph(workflow)

    assert [n.task_id for n in graph.nodes] == ["t1"]


@pytest.mark.parametrize(
    "node_id",
    ["t1", "T1", "001_products", "abc_DEF_123", "task1"],
)
def parse_graph_accepts_valid_node_ids_test(node_id: str) -> None:
    print(f"[{__name__}] parse_graph_accepts_valid_node_ids_test {node_id}")
    workflow = _fence(f"graph LR\n{node_id}")
    graph = parse_graph(workflow)

    assert [n.task_id for n in graph.nodes] == [node_id]


def parse_graph_missing_mermaid_block_raises_test() -> None:
    print(f"[{__name__}] parse_graph_missing_mermaid_block_raises_test")
    with pytest.raises(ValueError, match="missing ```mermaid``` block"):
        parse_graph("# No mermaid block here\n")


def parse_graph_empty_workflow_raises_test() -> None:
    print(f"[{__name__}] parse_graph_empty_workflow_raises_test")
    with pytest.raises(ValueError, match="missing ```mermaid``` block"):
        parse_graph("")


def parse_graph_missing_directive_raises_test() -> None:
    print(f"[{__name__}] parse_graph_missing_directive_raises_test")
    workflow = _fence("t1 --> t2")
    with pytest.raises(ValueError, match="graph <direction>"):
        parse_graph(workflow)


def parse_graph_duplicate_directive_raises_test() -> None:
    print(f"[{__name__}] parse_graph_duplicate_directive_raises_test")
    workflow = _fence("graph LR\ngraph TD\nt1")
    with pytest.raises(ValueError, match="duplicate graph directive"):
        parse_graph(workflow)


def parse_graph_no_tasks_raises_test() -> None:
    print(f"[{__name__}] parse_graph_no_tasks_raises_test")
    workflow = _fence("graph LR")
    with pytest.raises(ValueError, match="no tasks declared"):
        parse_graph(workflow)


def parse_graph_unrecognised_line_raises_test() -> None:
    print(f"[{__name__}] parse_graph_unrecognised_line_raises_test")
    workflow = _fence("graph LR\nt1 [bad syntax]")
    with pytest.raises(ValueError, match="unrecognised mermaid line"):
        parse_graph(workflow)


def parse_graph_invalid_node_name_in_edge_raises_test() -> None:
    print(f"[{__name__}] parse_graph_invalid_node_name_in_edge_raises_test")
    workflow = _fence("graph LR\nt1 --> t-2")
    with pytest.raises(ValueError, match="unrecognised mermaid line"):
        parse_graph(workflow)


def parse_graph_invalid_node_name_standalone_raises_test() -> None:
    print(f"[{__name__}] parse_graph_invalid_node_name_standalone_raises_test")
    workflow = _fence("graph LR\nbad name")
    with pytest.raises(ValueError, match="unrecognised mermaid line"):
        parse_graph(workflow)


def parse_graph_unknown_direction_raises_test() -> None:
    print(f"[{__name__}] parse_graph_unknown_direction_raises_test")
    workflow = _fence("graph XX\nt1")
    with pytest.raises(ValueError, match="unrecognised mermaid line"):
        parse_graph(workflow)
