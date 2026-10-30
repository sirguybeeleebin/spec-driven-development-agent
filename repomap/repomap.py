from __future__ import annotations

from pathlib import Path
from typing import Protocol

from models import State
from repomap.models import Tag


class Parser(Protocol):
    @property
    def extensions(self) -> frozenset[str]: ...

    def extract(self, source: bytes) -> list[Tag]: ...


class RepoMap:
    def __init__(
        self,
        parser: Parser,
        root: Path,
        max_tokens: int = 2000,
    ) -> None:
        print(f"[{__name__}] __init__ root={root} max_tokens={max_tokens}")
        self._parser = parser
        self._root = root.resolve()
        self._max_tokens = max_tokens

    def render(self, state: State) -> str:
        task_id = state["task_id"]
        target = state["target"]
        interfaces = state["interfaces"]

        print(f"[{__name__}] render task_id={task_id} target={target}")
        root = self._root
        if not root.is_dir():
            raise ValueError(f"repomap: workspace root not found: {root}")

        by_file: dict[str, list[Tag]] = {}
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix not in self._parser.extensions:
                continue
            rel = path.relative_to(root).as_posix()
            by_file[rel] = self._parser.extract(path.read_bytes())

        defs: dict[str, tuple[str, Tag]] = {}
        by_name: dict[str, list[str]] = {}
        for rel, tags in by_file.items():
            for tag in tags:
                if tag.kind not in ("class", "function", "field"):
                    continue
                key = f"{rel}::{'::'.join(tag.scope + (tag.name,))}"
                defs[key] = (rel, tag)
                by_name.setdefault(tag.name, []).append(key)

        if not defs:
            return ""

        edges: list[tuple[str, str]] = []
        for rel, tags in by_file.items():
            for tag in tags:
                if tag.kind != "ref" or tag.caller is None:
                    continue
                caller_key = f"{rel}::{tag.caller}"
                if caller_key not in defs:
                    continue
                for target_key in by_name.get(tag.name, []):
                    if target_key != caller_key:
                        edges.append((caller_key, target_key))

        symbol_names: set[str] = set()
        for interface in interfaces:
            for tag in self._parser.extract(interface.content.encode("utf-8")):
                if tag.kind in ("class", "function") and tag.scope == ():
                    symbol_names.add(tag.name)

        seeds: set[str] = set()
        for key, (rel, tag) in defs.items():
            if rel == target and tag.scope == () and tag.name in symbol_names:
                seeds.add(key)

        nodes = list(defs.keys())
        n = len(nodes)
        d = 0.85
        if seeds:
            prior = {k: (1.0 if k in seeds else 0.0) / len(seeds) for k in nodes}
        else:
            prior = dict.fromkeys(nodes, 1.0 / n)

        outgoing: dict[str, list[str]] = {k: [] for k in nodes}
        incoming: dict[str, list[str]] = {k: [] for k in nodes}
        for src, dst in edges:
            outgoing[src].append(dst)
            incoming[dst].append(src)

        score = dict(prior)
        for _ in range(30):
            new_score: dict[str, float] = {}
            for k in nodes:
                s = (1 - d) * prior[k]
                for inc in incoming[k]:
                    if outgoing[inc]:
                        s += d * score[inc] / len(outgoing[inc])
                new_score[k] = s
            score = new_score

        ranked = sorted(nodes, key=lambda k: (-score[k], k))
        budget_chars = self._max_tokens * 4
        selected: list[str] = []
        used = 0
        selected_rels: set[str] = set()
        for key in ranked:
            rel, tag = defs[key]
            indent_len = 4 * len(tag.scope)
            cost = len(rel) + 2 if rel not in selected_rels else 0
            for hl in tag.header.splitlines():
                cost += len(hl) + indent_len + 2
            if tag.docstring:
                doc_indent_len = indent_len + 4
                doc_lines = tag.docstring.splitlines()
                cost += len(tag.docstring) + doc_indent_len * len(doc_lines) + 8
            if used + cost > budget_chars:
                continue
            selected.append(key)
            used += cost
            selected_rels.add(rel)

        if not selected:
            return ""

        by_sel_file: dict[str, list[Tag]] = {}
        for key in selected:
            rel, tag = defs[key]
            by_sel_file.setdefault(rel, []).append(tag)

        file_max: dict[str, float] = {}
        for rel, tags in by_sel_file.items():
            file_max[rel] = max(
                score[f"{rel}::{'::'.join(t.scope + (t.name,))}"] for t in tags
            )
        ordered_files = sorted(by_sel_file.keys(), key=lambda r: (-file_max[r], r))

        parts: list[str] = []
        for rel in ordered_files:
            tags = sorted(by_sel_file[rel], key=lambda t: t.line)
            lines: list[str] = [f"{rel}:"]

            module_doc = next(
                (t for t in by_file[rel] if t.kind == "module_docstring"),
                None,
            )
            prev_end = -1
            if module_doc is not None:
                for hl in module_doc.header.splitlines():
                    lines.append("│" + hl)
                prev_end = module_doc.line + len(module_doc.header.splitlines())

            for tag in tags:
                if prev_end >= 0 and tag.line - prev_end > 1:
                    lines.append("⋮...")
                indent = "    " * len(tag.scope)
                for hl in tag.header.splitlines():
                    lines.append("│" + indent + hl)
                if tag.docstring:
                    doc_indent = indent + "    "
                    doc_lines = tag.docstring.splitlines()
                    if len(doc_lines) == 1:
                        lines.append("│" + doc_indent + '"""' + doc_lines[0] + '"""')
                    else:
                        lines.append("│" + doc_indent + '"""')
                        for dl in doc_lines:
                            lines.append("│" + doc_indent + dl)
                        lines.append("│" + doc_indent + '"""')
                prev_end = (
                    tag.line
                    + len(tag.header.splitlines())
                    + (len(tag.docstring.splitlines()) + 2 if tag.docstring else 0)
                )

            parts.append("\n".join(lines))

        result = "\n\n".join(parts)
        print(f"[{__name__}] render ok files={len(parts)} len={len(result)}")
        return result