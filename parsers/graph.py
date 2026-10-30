# parsers/graph.py

from __future__ import annotations

import re

from models import Edge, Graph, Node

_MERMAID_FENCE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
_DIRECTIVE = re.compile(r"^graph\s+(?:LR|RL|TD|TB|BT)$", re.IGNORECASE)
_NODE = re.compile(r"^[A-Za-z0-9_]+$")


def parse_graph(workflow: str) -> Graph:
    fence = _MERMAID_FENCE.search(workflow)
    if fence is None:
        raise ValueError("missing ```mermaid``` block")

    node_ids: list[str] = []
    seen_nodes: set[str] = set()
    edges: list[Edge] = []
    directive_seen = False

    for raw_line in fence.group(1).splitlines():
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
                source, target = parts[i], parts[i + 1]
                edges.append(Edge(source=source, target=target))
                if source not in seen_nodes:
                    seen_nodes.add(source)
                    node_ids.append(source)
                if target not in seen_nodes:
                    seen_nodes.add(target)
                    node_ids.append(target)
            continue
        if _NODE.match(line):
            if line not in seen_nodes:
                seen_nodes.add(line)
                node_ids.append(line)
            continue
        raise ValueError(f"unrecognised mermaid line: {line!r}")

    if not directive_seen:
        raise ValueError("missing 'graph <direction>' directive")
    if not node_ids:
        raise ValueError("no tasks declared")

    return Graph(
        nodes=[Node(task_id=tid) for tid in node_ids],
        edges=edges,
    )
