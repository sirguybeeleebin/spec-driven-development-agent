from __future__ import annotations

from pathlib import Path

import pytest

from models import Interface, Task
from repomap.models import Tag
from repomap.repomap import RepoMap


class FakeParser:
    def __init__(self, tags_by_source: dict[bytes, list[Tag]]) -> None:
        self._tags_by_source = tags_by_source

    @property
    def extensions(self) -> frozenset[str]:
        return frozenset({".py"})

    def extract(self, source: bytes) -> list[Tag]:
        return self._tags_by_source.get(source, [])


def _task(
    target: str,
    interfaces: list[Interface],
) -> Task:
    return Task(
        task_id="t1",
        goal="g",
        target=target,
        target_test="test.py",
        interfaces=interfaces,
        scenarios=[],
    )


def _tag(
    name: str,
    kind: str,
    *,
    scope: tuple[str, ...] = (),
    header: str = "",
    docstring: str = "",
    line: int = 1,
    caller: str | None = None,
) -> Tag:
    return Tag(
        name=name,
        kind=kind,
        scope=scope,
        header=header,
        docstring=docstring,
        line=line,
        caller=caller,
    )


def _workspace(
    tmp_path: Path,
    files: dict[str, list[Tag]],
) -> dict[bytes, list[Tag]]:
    tags_by_source: dict[bytes, list[Tag]] = {}
    for rel, tags in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        body = f"# {rel}\n".encode()
        path.write_bytes(body)
        tags_by_source[body] = tags
    return tags_by_source


def repomap_missing_root_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_missing_root_test")
    repomap = RepoMap(
        parser=FakeParser({}),
        root=tmp_path / "does-not-exist",
    )
    with pytest.raises(ValueError, match="workspace root not found"):
        repomap.render(_task("a.py", []))


def repomap_empty_workspace_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_empty_workspace_test")
    repomap = RepoMap(parser=FakeParser({}), root=tmp_path)
    assert repomap.render(_task("a.py", [])) == ""


def repomap_no_definitions_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_no_definitions_test")
    tags_by_source = _workspace(
        tmp_path,
        {
            "a.py": [
                _tag("", "module_docstring", header='"""doc"""'),
                _tag("helper", "ref", caller="run"),
            ]
        },
    )
    repomap = RepoMap(parser=FakeParser(tags_by_source), root=tmp_path)
    assert repomap.render(_task("a.py", [])) == ""


def repomap_renders_definition_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_renders_definition_test")
    tags_by_source = _workspace(
        tmp_path,
        {
            "a.py": [
                _tag(
                    "add",
                    "function",
                    header="def add(a, b):",
                    line=1,
                ),
            ]
        },
    )
    repomap = RepoMap(parser=FakeParser(tags_by_source), root=tmp_path)
    output = repomap.render(_task("a.py", []))
    assert "a.py:" in output
    assert "│def add(a, b):" in output


def repomap_seeds_focus_task_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_seeds_focus_task_test")
    tags_by_source = _workspace(
        tmp_path,
        {
            "a.py": [
                _tag("focus", "function", header="def focus():", line=1),
            ],
            "b.py": [
                _tag("other", "function", header="def other():", line=1),
            ],
        },
    )
    repomap = RepoMap(
        parser=FakeParser(tags_by_source),
        root=tmp_path,
        max_tokens=10_000,
    )
    task = _task(
        target="a.py",
        interfaces=[Interface(name="focus", content="def focus(): ...")],
    )
    output = repomap.render(task)
    assert output.index("a.py:") < output.index("b.py:")


def repomap_page_rank_follows_edges_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_page_rank_follows_edges_test")
    interface_source = b"def seed(): ..."
    tags_by_source = _workspace(
        tmp_path,
        {
            "a.py": [
                _tag("seed", "function", header="def seed():", line=1),
                _tag("helper", "ref", caller="seed"),
            ],
            "b.py": [
                _tag("helper", "function", header="def helper():", line=1),
            ],
            "c.py": [
                _tag("unrelated", "function", header="def unrelated():", line=1),
            ],
        },
    )
    tags_by_source[interface_source] = [
        _tag("seed", "function", header="def seed():", line=1),
    ]
    repomap = RepoMap(
        parser=FakeParser(tags_by_source),
        root=tmp_path,
        max_tokens=10_000,
    )
    task = _task(
        target="a.py",
        interfaces=[Interface(name="seed", content=interface_source.decode())],
    )
    output = repomap.render(task)
    a_pos = output.index("a.py:")
    b_pos = output.index("b.py:")
    c_pos = output.index("c.py:")
    assert a_pos < b_pos < c_pos


def repomap_budget_truncates_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_budget_truncates_test")
    tags_by_source = _workspace(
        tmp_path,
        {
            "a.py": [
                _tag(
                    name=f"fn{i}",
                    kind="function",
                    header=f"def fn{i}():",
                    line=i + 1,
                )
                for i in range(20)
            ]
        },
    )
    repomap = RepoMap(
        parser=FakeParser(tags_by_source),
        root=tmp_path,
        max_tokens=10,
    )
    output = repomap.render(_task("a.py", []))
    assert "fn0" in output
    assert "fn19" not in output


def repomap_renders_module_docstring_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_renders_module_docstring_test")
    tags_by_source = _workspace(
        tmp_path,
        {
            "a.py": [
                _tag(
                    "",
                    "module_docstring",
                    header='"""Module doc."""',
                    line=1,
                ),
                _tag("add", "function", header="def add():", line=3),
            ]
        },
    )
    repomap = RepoMap(parser=FakeParser(tags_by_source), root=tmp_path)
    output = repomap.render(_task("a.py", []))
    assert '│"""Module doc."""' in output
    assert "│def add():" in output


def repomap_renders_scope_indent_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_renders_scope_indent_test")
    tags_by_source = _workspace(
        tmp_path,
        {
            "a.py": [
                _tag("Box", "class", header="class Box:", line=1),
                _tag(
                    "get",
                    "function",
                    scope=("Box",),
                    header="def get(self):",
                    line=3,
                ),
            ]
        },
    )
    repomap = RepoMap(parser=FakeParser(tags_by_source), root=tmp_path)
    output = repomap.render(_task("a.py", []))
    assert "│class Box:" in output
    assert "│    def get(self):" in output


def repomap_renders_single_line_docstring_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_renders_single_line_docstring_test")
    tags_by_source = _workspace(
        tmp_path,
        {
            "a.py": [
                _tag(
                    "add",
                    "function",
                    header="def add():",
                    docstring="Adds numbers.",
                    line=1,
                ),
            ]
        },
    )
    repomap = RepoMap(parser=FakeParser(tags_by_source), root=tmp_path)
    output = repomap.render(_task("a.py", []))
    assert '│    """Adds numbers."""' in output


def repomap_renders_multiline_docstring_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_renders_multiline_docstring_test")
    tags_by_source = _workspace(
        tmp_path,
        {
            "a.py": [
                _tag(
                    "add",
                    "function",
                    header="def add():",
                    docstring="Line one.\nLine two.",
                    line=1,
                ),
            ]
        },
    )
    repomap = RepoMap(parser=FakeParser(tags_by_source), root=tmp_path)
    output = repomap.render(_task("a.py", []))
    assert '│    """' in output
    assert "│    Line one." in output
    assert "│    Line two." in output


def repomap_ellipsis_between_gaps_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_ellipsis_between_gaps_test")
    tags_by_source = _workspace(
        tmp_path,
        {
            "a.py": [
                _tag("first", "function", header="def first():", line=1),
                _tag("later", "function", header="def later():", line=50),
            ]
        },
    )
    repomap = RepoMap(parser=FakeParser(tags_by_source), root=tmp_path)
    output = repomap.render(_task("a.py", []))
    assert "⋮..." in output


def repomap_field_rendered_test(tmp_path: Path) -> None:
    print(f"[{__name__}] repomap_field_rendered_test")
    tags_by_source = _workspace(
        tmp_path,
        {
            "a.py": [
                _tag("Box", "class", header="class Box:", line=1),
                _tag(
                    "size",
                    "field",
                    scope=("Box",),
                    header="size: int",
                    line=2,
                ),
            ]
        },
    )
    repomap = RepoMap(parser=FakeParser(tags_by_source), root=tmp_path)
    output = repomap.render(_task("a.py", []))
    assert "│class Box:" in output
    assert "│    size: int" in output
