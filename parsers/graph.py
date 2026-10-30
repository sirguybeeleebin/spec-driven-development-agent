# parsers/graph.py

from __future__ import annotations

import re

from models import Edge, Graph, Node

_MERMAID_FENCE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
_DIRECTIVE = re.compile(r"^graph\s+(?:LR|RL|TD|TB|BT)$", re.IGNORECASE)
_NODE = re.compile(r"^[A-Za-z0-9_]+$")


def parse_graph(graph: str) -> Graph:
    fence = _MERMAID_FENCE.search(graph)
    if fence is None:
        raise ValueError("missing ```mermaid``` block")
    body = fence.group(1)

    nodes: dict[str, Node] = {}
    edges: list[Edge] = []
    declared: set[str] = set()
    seen_edges: set[tuple[str, str]] = set()
    directive_seen = False

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if _DIRECTIVE.match(line):
            if directive_seen:
                raise ValueError("duplicate graph directive")
            directive_seen = True
            continue

        if "-->" in line:
            parts = [p.strip() for p in line.split("-->")]
            for part in parts:
                if not _NODE.match(part):
                    raise ValueError(f"unrecognised mermaid line: {line!r}")
            for i in range(len(parts) - 1):
                src_id, tgt_id = parts[i], parts[i + 1]
                if src_id == tgt_id:
                    raise ValueError(f"graph: self-loop at {src_id!r}")
                key = (src_id, tgt_id)
                if key in seen_edges:
                    raise ValueError(f"graph: duplicate edge {src_id!r} --> {tgt_id!r}")
                seen_edges.add(key)
                src = nodes.setdefault(src_id, Node(task_id=src_id))
                tgt = nodes.setdefault(tgt_id, Node(task_id=tgt_id))
                edges.append(Edge(source=src, target=tgt))
            continue

        if _NODE.match(line):
            if line in declared:
                raise ValueError(f"graph: duplicate node {line!r}")
            declared.add(line)
            nodes.setdefault(line, Node(task_id=line))
            continue

        raise ValueError(f"unrecognised mermaid line: {line!r}")

    if not directive_seen:
        raise ValueError("missing 'graph <direction>' directive")
    if not nodes:
        raise ValueError("no tasks declared")

    adjacency: dict[str, list[str]] = {task_id: [] for task_id in nodes}
    for edge in edges:
        adjacency[edge.source.task_id].append(edge.target.task_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            raise ValueError(f"graph: cycle detected at {task_id!r}")
        visiting.add(task_id)
        for child in adjacency[task_id]:
            visit(child)
        visiting.discard(task_id)
        visited.add(task_id)

    for task_id in adjacency:
        visit(task_id)

    return Graph(nodes=list(nodes.values()), edges=edges)
