# parsers/graph_test.py

from __future__ import annotations

import pytest

from models import Edge, Graph, Node
from parsers.graph import parse_graph

# The parser is only aware of the shape `Node(task_id=...)` /
# `Edge(source=..., target=...)`. If those models gain required fields,
# adapt the constructors in `_mermaid` accordingly — the tests only
# inspect `task_id`, `source.task_id`, `target.task_id` and object
# identity between edge endpoints and the node list.

# ---- helpers ----


def _mermaid(body: str) -> str:
    return f"```mermaid\n{body}\n```"


# ---- happy paths ----


def test_single_node_with_directive() -> None:
    g = parse_graph(_mermaid("graph LR\nA"))
    assert isinstance(g, Graph)
    assert [n.task_id for n in g.nodes] == ["A"]
    assert g.edges == []


def test_single_edge() -> None:
    g = parse_graph(_mermaid("graph LR\nA --> B"))
    assert [n.task_id for n in g.nodes] == ["A", "B"]
    assert len(g.edges) == 1
    assert g.edges[0].source.task_id == "A"
    assert g.edges[0].target.task_id == "B"


def test_chain_edge_in_one_line() -> None:
    g = parse_graph(_mermaid("graph LR\nA --> B --> C"))
    assert [n.task_id for n in g.nodes] == ["A", "B", "C"]
    assert [(e.source.task_id, e.target.task_id) for e in g.edges] == [
        ("A", "B"),
        ("B", "C"),
    ]


def test_multiple_edges_on_separate_lines_preserve_order() -> None:
    g = parse_graph(_mermaid("graph LR\nA --> B\nB --> C\nC --> D"))
    assert [(e.source.task_id, e.target.task_id) for e in g.edges] == [
        ("A", "B"),
        ("B", "C"),
        ("C", "D"),
    ]


def test_multiple_chains_combine() -> None:
    g = parse_graph(_mermaid("graph LR\nA --> B --> C\nD --> E"))
    assert [(e.source.task_id, e.target.task_id) for e in g.edges] == [
        ("A", "B"),
        ("B", "C"),
        ("D", "E"),
    ]


def test_nodes_preserved_in_insertion_order() -> None:
    g = parse_graph(_mermaid("graph LR\nA --> B\nC\nD --> E"))
    assert [n.task_id for n in g.nodes] == ["A", "B", "C", "D", "E"]


def test_node_only_lines_create_nodes() -> None:
    g = parse_graph(_mermaid("graph LR\nA\nB\nC"))
    assert [n.task_id for n in g.nodes] == ["A", "B", "C"]
    assert g.edges == []


def test_mixed_node_and_edge_lines() -> None:
    g = parse_graph(_mermaid("graph LR\nA\nA --> B\nB --> C"))
    assert [n.task_id for n in g.nodes] == ["A", "B", "C"]


def test_edge_endpoints_are_same_instances_as_node_list() -> None:
    g = parse_graph(_mermaid("graph LR\nA --> B --> C"))
    by_id = {n.task_id: n for n in g.nodes}
    for edge in g.edges:
        assert edge.source is by_id[edge.source.task_id]
        assert edge.target is by_id[edge.target.task_id]


def test_node_line_does_not_duplicate_node_already_from_edge() -> None:
    g = parse_graph(_mermaid("graph LR\nA --> B\nB"))
    assert [n.task_id for n in g.nodes] == ["A", "B"]


def test_node_declared_after_edge_use_is_ok() -> None:
    # Edge auto-creates A and B; a later `A` line is the first *explicit*
    # declaration, so it is not a duplicate.
    g = parse_graph(_mermaid("graph LR\nA --> B\nA"))
    assert [n.task_id for n in g.nodes] == ["A", "B"]
    assert [(e.source.task_id, e.target.task_id) for e in g.edges] == [
        ("A", "B"),
    ]


def test_edge_alone_declares_both_nodes() -> None:
    g = parse_graph(_mermaid("graph LR\nX --> Y"))
    assert [n.task_id for n in g.nodes] == ["X", "Y"]


def test_underscore_and_digits_allowed_in_ids() -> None:
    g = parse_graph(_mermaid("graph LR\nabc_123 --> _x9"))
    assert [n.task_id for n in g.nodes] == ["abc_123", "_x9"]


def test_all_node_names_from_mermaid_spec_charset() -> None:
    # `_NODE` = `^[A-Za-z0-9_]+$`
    g = parse_graph(_mermaid("graph LR\nA1\nb_2\n_C3"))
    assert [n.task_id for n in g.nodes] == ["A1", "b_2", "_C3"]


# ---- directive handling ----


@pytest.mark.parametrize(
    "directive",
    ["graph LR", "graph RL", "graph TD", "graph TB", "graph BT"],
)
def test_all_valid_directions_accepted(directive: str) -> None:
    g = parse_graph(_mermaid(f"{directive}\nA"))
    assert [n.task_id for n in g.nodes] == ["A"]


@pytest.mark.parametrize(
    "directive",
    ["GRAPH LR", "Graph LR", "graph lr", "GrApH tD", "graph  LR", "graph\tLR"],
)
def test_directive_is_case_insensitive_and_tolerates_whitespace(
    directive: str,
) -> None:
    g = parse_graph(_mermaid(f"{directive}\nA"))
    assert [n.task_id for n in g.nodes] == ["A"]


def test_directive_may_appear_after_nodes() -> None:
    # The parser scans every line; ordering is not enforced.
    g = parse_graph(_mermaid("A\ngraph LR\nA --> B"))
    assert [n.task_id for n in g.nodes] == ["A", "B"]


# ---- whitespace handling ----


def test_leading_and_trailing_whitespace_tolerated() -> None:
    g = parse_graph(_mermaid("  graph LR  \n  A   \n   A   -->   B  "))
    assert [n.task_id for n in g.nodes] == ["A", "B"]
    assert g.edges[0].source.task_id == "A"


@pytest.mark.parametrize(
    "edge_line",
    ["A-->B", "A --> B", "A  -->  B", "A\t-->\tB", " A --> B "],
)
def test_arrow_whitespace_tolerant(edge_line: str) -> None:
    g = parse_graph(_mermaid(f"graph LR\n{edge_line}"))
    assert [(e.source.task_id, e.target.task_id) for e in g.edges] == [("A", "B")]


def test_blank_lines_skipped() -> None:
    g = parse_graph(_mermaid("\n\ngraph LR\n\n\nA --> B\n\nC\n\n"))
    assert [n.task_id for n in g.nodes] == ["A", "B", "C"]


def test_only_first_mermaid_block_is_parsed() -> None:
    graph = "```mermaid\ngraph LR\nA\n```\n```mermaid\ngraph LR\nB\n```"
    g = parse_graph(graph)
    assert [n.task_id for n in g.nodes] == ["A"]


# ---- errors: fence / directive ----


def test_missing_mermaid_block_raises() -> None:
    with pytest.raises(ValueError, match=r"missing ```mermaid``` block"):
        parse_graph("graph LR\nA")


def test_wrong_fence_language_raises() -> None:
    with pytest.raises(ValueError, match=r"missing ```mermaid``` block"):
        parse_graph("```python\ngraph LR\nA\n```")


def test_empty_string_raises() -> None:
    with pytest.raises(ValueError, match=r"missing ```mermaid``` block"):
        parse_graph("")


def test_duplicate_directive_raises() -> None:
    with pytest.raises(ValueError, match="duplicate graph directive"):
        parse_graph(_mermaid("graph LR\ngraph TD\nA"))


def test_missing_directive_raises() -> None:
    with pytest.raises(ValueError, match=r"missing 'graph <direction>' directive"):
        parse_graph(_mermaid("A --> B"))


def test_directive_alone_without_nodes_raises_no_tasks() -> None:
    with pytest.raises(ValueError, match="no tasks declared"):
        parse_graph(_mermaid("graph LR"))


def test_blank_body_raises_missing_directive() -> None:
    with pytest.raises(ValueError, match=r"missing 'graph <direction>' directive"):
        parse_graph(_mermaid(""))


# ---- errors: bad nodes / bad lines ----


def test_invalid_direction_raises_unrecognised() -> None:
    with pytest.raises(ValueError, match="unrecognised mermaid line"):
        parse_graph(_mermaid("graph XY\nA"))


def test_directive_with_extra_content_raises_unrecognised() -> None:
    with pytest.raises(ValueError, match="unrecognised mermaid line"):
        parse_graph(_mermaid("graph LR extra\nA"))


@pytest.mark.parametrize(
    "bad_id",
    ["a-b", "a.b", "a b", "a/b", "a:b"],
)
def test_node_with_invalid_characters_raises(bad_id: str) -> None:
    with pytest.raises(ValueError, match="unrecognised mermaid line"):
        parse_graph(_mermaid(f"graph LR\n{bad_id}"))


def test_invalid_node_inside_edge_raises() -> None:
    with pytest.raises(ValueError, match="unrecognised mermaid line"):
        parse_graph(_mermaid("graph LR\nA --> B-C"))


def test_empty_node_on_left_of_arrow_raises() -> None:
    with pytest.raises(ValueError, match="unrecognised mermaid line"):
        parse_graph(_mermaid("graph LR\n--> B"))


def test_empty_node_on_right_of_arrow_raises() -> None:
    with pytest.raises(ValueError, match="unrecognised mermaid line"):
        parse_graph(_mermaid("graph LR\nA -->"))


def test_double_dash_without_arrow_raises() -> None:
    with pytest.raises(ValueError, match="unrecognised mermaid line"):
        parse_graph(_mermaid("graph LR\nA -- B"))


def test_arbitrary_line_raises() -> None:
    with pytest.raises(ValueError, match="unrecognised mermaid line"):
        parse_graph(_mermaid("graph LR\nthis is not mermaid"))


def test_error_message_includes_offending_line() -> None:
    with pytest.raises(ValueError) as excinfo:
        parse_graph(_mermaid("graph LR\nA --> B-C"))
    assert "A --> B-C" in str(excinfo.value)


# ---- errors: self-loops ----


def test_self_loop_raises() -> None:
    with pytest.raises(ValueError, match=r"self-loop at 'A'"):
        parse_graph(_mermaid("graph LR\nA --> A"))


def test_self_loop_in_chain_raises() -> None:
    with pytest.raises(ValueError, match=r"self-loop at 'B'"):
        parse_graph(_mermaid("graph LR\nA --> B --> B"))


def test_self_loop_message_does_not_say_cycle() -> None:
    # Distinguish self-loop from a genuine cycle in the error message.
    with pytest.raises(ValueError) as exc:
        parse_graph(_mermaid("graph LR\nA --> A"))
    msg = str(exc.value)
    assert "self-loop" in msg
    assert "cycle" not in msg


# ---- errors: duplicate edges ----


def test_duplicate_edge_raises() -> None:
    with pytest.raises(ValueError, match=r"duplicate edge 'A' --> 'B'"):
        parse_graph(_mermaid("graph LR\nA --> B\nA --> B"))


def test_duplicate_edge_via_chain_raises() -> None:
    with pytest.raises(ValueError, match=r"duplicate edge"):
        parse_graph(_mermaid("graph LR\nA --> B --> C\nA --> B"))


def test_duplicate_edge_reverse_order_not_duplicate() -> None:
    # A --> B and B --> A are two different edges (and a cycle, caught
    # later by the cycle detector).
    with pytest.raises(ValueError, match=r"cycle detected"):
        parse_graph(_mermaid("graph LR\nA --> B\nB --> A"))


# ---- errors: duplicate nodes ----


def test_duplicate_node_raises() -> None:
    with pytest.raises(ValueError, match=r"duplicate node 'A'"):
        parse_graph(_mermaid("graph LR\nA\nA"))


def test_duplicate_node_after_edge_declaration_raises() -> None:
    # Explicit `A` line twice, even with an edge in between.
    with pytest.raises(ValueError, match=r"duplicate node 'A'"):
        parse_graph(_mermaid("graph LR\nA\nA --> B\nA"))


# ---- errors: cycles ----


def test_simple_cycle_raises() -> None:
    with pytest.raises(ValueError, match=r"cycle detected at 'A'"):
        parse_graph(_mermaid("graph LR\nA --> B\nB --> A"))


def test_longer_cycle_raises() -> None:
    with pytest.raises(ValueError, match="cycle detected"):
        parse_graph(_mermaid("graph LR\nA --> B\nB --> C\nC --> A"))


def test_cycle_detected_even_with_dangling_branch() -> None:
    with pytest.raises(ValueError, match="cycle detected"):
        parse_graph(_mermaid("graph LR\nD\nA --> B\nB --> C\nC --> B"))


# ---- valid DAGs that must not raise ----


def test_diamond_is_not_a_cycle() -> None:
    # A → B, A → C, B → D, C → D
    g = parse_graph(_mermaid("graph LR\nA --> B\nA --> C\nB --> D\nC --> D"))
    assert [n.task_id for n in g.nodes] == ["A", "B", "C", "D"]
    assert len(g.edges) == 4


def test_transitive_edge_is_allowed() -> None:
    # A --> C alongside A --> B --> C is redundant, but not an error:
    # it is still a DAG, just not transitively reduced.
    g = parse_graph(_mermaid("graph LR\nA --> B\nB --> C\nA --> C"))
    assert [(e.source.task_id, e.target.task_id) for e in g.edges] == [
        ("A", "B"),
        ("B", "C"),
        ("A", "C"),
    ]


def test_chain_does_not_false_positive() -> None:
    # Long linear chain must not trip the cycle detector.
    body = "\n".join(f"N{i} --> N{i + 1}" for i in range(10))
    g = parse_graph(_mermaid(f"graph LR\n{body}"))
    assert len(g.nodes) == 11
    assert len(g.edges) == 10


def test_parallel_independent_chains() -> None:
    # Two disjoint chains — no shared nodes, no shared edges.
    g = parse_graph(_mermaid("graph LR\nA --> B\nC --> D"))
    assert [(e.source.task_id, e.target.task_id) for e in g.edges] == [
        ("A", "B"),
        ("C", "D"),
    ]


# ---- return shape ----


def test_returns_graph_instance_with_node_and_edge_dataclasses() -> None:
    g = parse_graph(_mermaid("graph LR\nA --> B"))
    assert isinstance(g, Graph)
    assert all(isinstance(n, Node) for n in g.nodes)
    assert all(isinstance(e, Edge) for e in g.edges)


def test_empty_edges_returns_empty_list_not_none() -> None:
    g = parse_graph(_mermaid("graph LR\nA"))
    assert g.edges == []
    assert isinstance(g.edges, list)
    assert isinstance(g.nodes, list)
