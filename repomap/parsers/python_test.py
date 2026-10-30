from __future__ import annotations

from repomap.parsers.python import PythonParser


def _parser() -> PythonParser:
    return PythonParser()


def python_parser_extensions_test() -> None:
    print(f"[{__name__}] python_parser_extensions_test")
    assert _parser().extensions == frozenset({".py", ".pyi"})


def python_parser_empty_source_test() -> None:
    print(f"[{__name__}] python_parser_empty_source_test")
    tags = _parser().extract(b"")
    assert tags == []


def python_parser_module_docstring_test() -> None:
    print(f"[{__name__}] python_parser_module_docstring_test")
    tags = _parser().extract(b'"""Module doc."""\n')
    assert len(tags) == 1
    tag = tags[0]
    assert tag.kind == "module_docstring"
    assert tag.name == ""
    assert tag.line == 1


def python_parser_simple_function_test() -> None:
    print(f"[{__name__}] python_parser_simple_function_test")
    source = (
        b"def add(a: int, b: int) -> int:\n"
        b'    """Add two numbers."""\n'
        b"    return a + b\n"
    )
    tags = _parser().extract(source)
    funcs = [t for t in tags if t.kind == "function"]
    assert len(funcs) == 1
    tag = funcs[0]
    assert tag.name == "add"
    assert tag.scope == ()
    assert "def add" in tag.header
    assert tag.docstring == "Add two numbers."
    assert tag.line == 1


def python_parser_class_with_method_test() -> None:
    print(f"[{__name__}] python_parser_class_with_method_test")
    source = (
        b"class Repo:\n"
        b'    """Repo doc."""\n'
        b"    def get(self, key: str) -> str:\n"
        b'        """Get a value."""\n'
        b"        return key\n"
    )
    tags = _parser().extract(source)
    classes = [t for t in tags if t.kind == "class"]
    methods = [t for t in tags if t.kind == "function"]
    assert len(classes) == 1
    assert classes[0].name == "Repo"
    assert classes[0].docstring == "Repo doc."
    assert len(methods) == 1
    assert methods[0].name == "get"
    assert methods[0].scope == ("Repo",)
    assert methods[0].docstring == "Get a value."


def python_parser_private_skipped_test() -> None:
    print(f"[{__name__}] python_parser_private_skipped_test")
    source = (
        b"def _private() -> None:\n"
        b"    pass\n"
        b"def public() -> None:\n"
        b"    pass\n"
        b"class _Hidden:\n"
        b"    pass\n"
    )
    tags = _parser().extract(source)
    names = {t.name for t in tags if t.kind in ("function", "class")}
    assert names == {"public"}


def python_parser_typed_field_test() -> None:
    print(f"[{__name__}] python_parser_typed_field_test")
    source = b"class Box:\n    size: int\n    name: str\n    _hidden: int\n"
    tags = _parser().extract(source)
    fields = [t for t in tags if t.kind == "field"]
    names = sorted(f.name for f in fields)
    assert names == ["name", "size"]
    for f in fields:
        assert f.scope == ("Box",)
        assert ":" in f.header


def python_parser_nested_functions_test() -> None:
    print(f"[{__name__}] python_parser_nested_functions_test")
    source = (
        b"def outer() -> None:\n    def inner() -> None:\n        pass\n    inner()\n"
    )
    tags = _parser().extract(source)
    funcs = [t for t in tags if t.kind == "function"]
    by_name = {t.name: t for t in funcs}
    assert set(by_name) == {"outer", "inner"}
    assert by_name["outer"].scope == ()
    assert by_name["inner"].scope == ("outer",)


def python_parser_decorated_function_test() -> None:
    print(f"[{__name__}] python_parser_decorated_function_test")
    source = (
        b"import functools\n"
        b"\n"
        b"@functools.cache\n"
        b"def fib(n: int) -> int:\n"
        b"    return n if n < 2 else fib(n - 1) + fib(n - 2)\n"
    )
    tags = _parser().extract(source)
    funcs = [t for t in tags if t.kind == "function"]
    assert any(t.name == "fib" for t in funcs)
    fib = next(t for t in funcs if t.name == "fib")
    assert "@functools.cache" in fib.header


def python_parser_call_ref_test() -> None:
    print(f"[{__name__}] python_parser_call_ref_test")
    source = b"def run() -> None:\n    helper()\n"
    tags = _parser().extract(source)
    refs = [t for t in tags if t.kind == "ref"]
    assert any(r.name == "helper" for r in refs)
    helper = next(r for r in refs if r.name == "helper")
    assert helper.caller == "run"


def python_parser_private_call_skipped_test() -> None:
    print(f"[{__name__}] python_parser_private_call_skipped_test")
    source = b"def run() -> None:\n    _hidden()\n"
    tags = _parser().extract(source)
    refs = [t for t in tags if t.kind == "ref"]
    assert all(r.name != "_hidden" for r in refs)


def python_parser_module_level_field_test() -> None:
    print(f"[{__name__}] python_parser_module_level_field_test")
    source = b'VERSION: str = "1.0"\n'
    tags = _parser().extract(source)
    fields = [t for t in tags if t.kind == "field"]
    assert len(fields) == 1
    assert fields[0].name == "VERSION"
    assert fields[0].scope == ()


def python_parser_untyped_assignment_not_field_test() -> None:
    print(f"[{__name__}] python_parser_untyped_assignment_not_field_test")
    source = b"X = 1\n"
    tags = _parser().extract(source)
    fields = [t for t in tags if t.kind == "field"]
    assert fields == []


def python_parser_multiline_function_header_test() -> None:
    print(f"[{__name__}] python_parser_multiline_function_header_test")
    source = b"def add(\n    a: int,\n    b: int,\n) -> int:\n    return a + b\n"
    tags = _parser().extract(source)
    funcs = [t for t in tags if t.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].name == "add"
    assert "def add(" in funcs[0].header
    assert "a: int" in funcs[0].header


def python_parser_comment_before_docstring_test() -> None:
    print(f"[{__name__}] python_parser_comment_before_docstring_test")
    source = b"def add() -> int:\n    # leading comment\n    return 1\n"
    tags = _parser().extract(source)
    funcs = [t for t in tags if t.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].docstring == ""
