from __future__ import annotations

import inspect

from tree_sitter import Node
from tree_sitter_language_pack import get_parser

from repomap.models import Tag


class PythonParser:
    def __init__(self) -> None:
        print(f"[{__name__}] __init__")
        self._parser = get_parser("python")

    @property
    def extensions(self) -> frozenset[str]:
        return frozenset({".py", ".pyi"})

    def extract(self, source: bytes) -> list[Tag]:
        print(f"[{__name__}] extract source_len={len(source)}")
        tree = self._parser.parse(source)
        root = tree.root_node
        tags: list[Tag] = []
        scope: list[str] = []

        def text(node: Node) -> str:
            return source[node.start_byte : node.end_byte].decode(
                "utf-8", errors="replace"
            )

        def is_docstring_literal(raw: str) -> bool:
            lower = raw.lower()
            for prefix in ("rb", "br", "rf", "fr"):
                if lower.startswith(prefix):
                    return False
            return True

        def strip_prefix(raw: str) -> str:
            lower = raw.lower()
            for prefix in ("rb", "br", "rf", "fr"):
                if lower.startswith(prefix):
                    return raw
            for prefix in ("r", "R", "u", "U"):
                if raw.startswith(prefix):
                    return raw[1:]
            return raw

        def clean_docstring(raw: str) -> str:
            raw = strip_prefix(raw.strip())
            for quote in ('"""', "'''", '"', "'"):
                if (
                    raw.startswith(quote)
                    and raw.endswith(quote)
                    and len(raw) >= 2 * len(quote)
                ):
                    raw = raw[len(quote) : -len(quote)]
                    break
            return inspect.cleandoc(raw)

        def docstring_of(body: Node) -> tuple[str, str]:
            for child in body.named_children:
                if child.type == "comment":
                    continue
                target = None
                if child.type in ("string", "concatenated_string"):
                    target = child
                elif child.type == "expression_statement":
                    for sub in child.named_children:
                        if sub.type in ("string", "concatenated_string"):
                            target = sub
                            break
                if target is None:
                    return ("", "")
                raw = text(target)
                if not is_docstring_literal(raw):
                    return ("", "")
                return (raw, clean_docstring(raw))
            return ("", "")

        # Module docstring: first non-comment child of the module root.
        module_raw, module_clean = docstring_of(root)
        if module_clean:
            tags.append(
                Tag(
                    name="",
                    kind="module_docstring",
                    header=strip_prefix(module_raw),
                    docstring="",
                    line=1,
                )
            )

        def emit_fields(body: Node) -> None:
            # Only typed assignments count as public fields. Modern
            # tree-sitter-python distinguishes annotated assignments from
            # plain assignments; accept both forms and any direct placement.
            for stmt in body.named_children:
                candidates: list[Node] = []
                if stmt.type == "expression_statement":
                    candidates = list(stmt.named_children)
                elif stmt.type in ("assignment", "annotated_assignment"):
                    candidates = [stmt]
                for sub in candidates:
                    if sub.type not in ("assignment", "annotated_assignment"):
                        continue
                    type_node = sub.child_by_field_name("type")
                    if type_node is None:
                        continue
                    left = sub.child_by_field_name("left")
                    if left is None or left.type != "identifier":
                        continue
                    fname = text(left)
                    if not fname or fname.startswith("_"):
                        continue
                    header = source[sub.start_byte : sub.end_byte].decode(
                        "utf-8", errors="replace"
                    )
                    tags.append(
                        Tag(
                            name=fname,
                            kind="field",
                            scope=tuple(scope),
                            header=header,
                            docstring="",
                            line=sub.start_point[0] + 1,
                        )
                    )

        def emit_def(outer: Node, inner: Node) -> None:
            name_node = inner.child_by_field_name("name")
            body = inner.child_by_field_name("body")
            if name_node is None or body is None:
                walk(outer)
                return
            name = text(name_node)
            if not name or name.startswith("_"):
                walk(outer)
                return
            header_end = body.start_byte
            while header_end > outer.start_byte and source[
                header_end - 1 : header_end
            ] in (b" ", b"\t", b"\n"):
                header_end -= 1
            header = source[outer.start_byte : header_end].decode(
                "utf-8", errors="replace"
            )
            _, doc = docstring_of(body)
            kind = "class" if inner.type == "class_definition" else "function"
            scope.append(name)
            tags.append(
                Tag(
                    name=name,
                    kind=kind,
                    scope=tuple(scope[:-1]),
                    header=header,
                    docstring=doc,
                    line=outer.start_point[0] + 1,
                )
            )
            if inner.type == "class_definition":
                emit_fields(body)
            walk(body)
            scope.pop()

        def walk(node: Node) -> None:
            for child in node.named_children:
                if child.type == "decorated_definition":
                    inner = child.child_by_field_name("definition")
                    if inner is None or inner.type not in (
                        "class_definition",
                        "function_definition",
                    ):
                        walk(child)
                        continue
                    emit_def(child, inner)
                elif child.type in ("class_definition", "function_definition"):
                    emit_def(child, child)
                elif child.type == "call":
                    func = child.child_by_field_name("function")
                    callee = ""
                    if func is not None:
                        if func.type == "identifier":
                            callee = text(func)
                        elif func.type == "attribute":
                            attr = func.child_by_field_name("attribute")
                            if attr is not None:
                                callee = text(attr)
                    if callee and not callee.startswith("_"):
                        tags.append(
                            Tag(
                                name=callee,
                                kind="ref",
                                caller="::".join(scope) if scope else None,
                                line=-1,
                            )
                        )
                    walk(child)
                else:
                    walk(child)

        # Module-level typed constants become fields with empty scope.
        emit_fields(root)
        walk(root)
        print(f"[{__name__}] extract ok tags={len(tags)}")
        return tags
