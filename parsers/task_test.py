# parsers/task_test.py

from __future__ import annotations

import pytest

from models import Gherkin, Interface, Sequence, Task
from parsers.task import parse_task

CONSTITUTION = "Follow the rules."


# ---- helpers ----


def _task_text(
    *,
    header: str = (
        "- task_id: t1\n- target_file: src/foo.py\n- target_test_file: src/foo_test.py"
    ),
    goal: str = "Build foo.",
    declares: str = "- Foo",
    interfaces: str = "```python\nclass Foo:\n    pass\n```",
    gherkins: str = (
        "## Foo: foo works\n```gherkin\nGiven a Foo\nWhen I call it\nThen it works\n```"
    ),
    sequence: str | None = None,
) -> str:
    """Build a task document. Every parameter can be overridden
    independently, so tests can pin one behaviour at a time."""
    parts = [
        "# Task",
        header,
        "",
        "# Goal",
        goal,
        "",
        "# Declares",
        declares,
        "",
        "# Interfaces",
        interfaces,
        "",
        "# Gherkins",
        gherkins,
    ]
    if sequence is not None:
        parts.extend(["", "# Sequence", sequence])
    return "\n".join(parts) + "\n"


# ---- constitution ----


def test_empty_constitution_raises() -> None:
    with pytest.raises(ValueError, match="constitution is empty"):
        parse_task(_task_text(), "")


def test_constitution_copied_verbatim() -> None:
    task = parse_task(_task_text(), "My custom constitution")
    assert task.constitution == "My custom constitution"


# ---- missing sections ----


@pytest.mark.parametrize(
    "section,marker",
    [
        ("Task", "# Task\n"),
        ("Goal", "# Goal\n"),
        ("Declares", "# Declares\n"),
        ("Interfaces", "# Interfaces\n"),
        ("Gherkins", "# Gherkins\n"),
    ],
)
def test_missing_section_raises(section: str, marker: str) -> None:
    text = _task_text().replace(marker, "", 1)
    with pytest.raises(ValueError, match=f"missing '# {section}' section"):
        parse_task(text, CONSTITUTION)


def test_sections_checked_in_documented_order() -> None:
    # Both Task and Goal are missing — Task must be reported first.
    text = _task_text().replace("# Task\n", "", 1).replace("# Goal\n", "", 1)
    with pytest.raises(ValueError, match="missing '# Task' section"):
        parse_task(text, CONSTITUTION)


# ---- header: task_id / target_file / target_test_file ----


def test_missing_task_id_raises() -> None:
    header = "- target_file: x\n- target_test_file: y"
    with pytest.raises(ValueError, match="missing 'task_id'"):
        parse_task(_task_text(header=header), CONSTITUTION)


def test_missing_target_file_raises() -> None:
    header = "- task_id: t1\n- target_test_file: y"
    with pytest.raises(ValueError, match="missing 'target_file'"):
        parse_task(_task_text(header=header), CONSTITUTION)


def test_missing_target_test_file_raises() -> None:
    header = "- task_id: t1\n- target_file: x"
    with pytest.raises(ValueError, match="missing 'target_test_file'"):
        parse_task(_task_text(header=header), CONSTITUTION)


def test_missing_target_file_reported_before_target_test_file() -> None:
    header = "- task_id: t1"
    with pytest.raises(ValueError, match="missing 'target_file'"):
        parse_task(_task_text(header=header), CONSTITUTION)


def test_empty_task_id_raises() -> None:
    # Trailing space: the regex backtracks to make `.+` match " ",
    # which then strips to empty.
    header = "- task_id: \n- target_file: x\n- target_test_file: y"
    with pytest.raises(ValueError, match="'task_id' is empty"):
        parse_task(_task_text(header=header), CONSTITUTION)


def test_empty_target_file_raises() -> None:
    header = "- task_id: t1\n- target_file: \n- target_test_file: y"
    with pytest.raises(ValueError, match="'target_file' is empty"):
        parse_task(_task_text(header=header), CONSTITUTION)


def test_empty_target_test_file_raises() -> None:
    header = "- task_id: t1\n- target_file: x\n- target_test_file: "
    with pytest.raises(ValueError, match="'target_test_file' is empty"):
        parse_task(_task_text(header=header), CONSTITUTION)


def test_header_values_stripped() -> None:
    header = (
        "- task_id:   t1   \n- target_file:   x.py   \n- target_test_file:   y.py   "
    )
    task = parse_task(_task_text(header=header), CONSTITUTION)
    assert task.task_id == "t1"
    assert task.target_file == "x.py"
    assert task.target_test_file == "y.py"


def test_extra_header_keys_ignored() -> None:
    header = (
        "- task_id: t1\n- target_file: x\n- target_test_file: y\n- extra: something"
    )
    task = parse_task(_task_text(header=header), CONSTITUTION)
    assert task.task_id == "t1"


# ---- goal ----


def test_empty_goal_raises() -> None:
    with pytest.raises(ValueError, match="goal is empty"):
        parse_task(_task_text(goal=""), CONSTITUTION)


def test_whitespace_only_goal_raises() -> None:
    with pytest.raises(ValueError, match="goal is empty"):
        parse_task(_task_text(goal="   \n\t  "), CONSTITUTION)


def test_goal_stripped() -> None:
    task = parse_task(_task_text(goal="  spaced goal  "), CONSTITUTION)
    assert task.goal == "spaced goal"


def test_multiline_goal_preserved() -> None:
    task = parse_task(_task_text(goal="Line one\nLine two"), CONSTITUTION)
    assert task.goal == "Line one\nLine two"


def test_hash_line_inside_goal_truncates_goal() -> None:
    # Quirk: `# anything` on its own line inside Goal is parsed as a
    # section header, splitting the goal.
    task = parse_task(
        _task_text(goal="Line one\n# not really a section\nLine two"),
        CONSTITUTION,
    )
    assert task.goal == "Line one"


# ---- declares ----


def test_empty_declares_raises() -> None:
    with pytest.raises(ValueError, match="empty '# Declares' section"):
        parse_task(_task_text(declares=""), CONSTITUTION)


def test_invalid_declare_line_raises() -> None:
    with pytest.raises(ValueError, match="cannot parse line"):
        parse_task(_task_text(declares="Foo"), CONSTITUTION)


def test_declare_with_hyphen_rejected() -> None:
    with pytest.raises(ValueError, match="cannot parse line"):
        parse_task(_task_text(declares="- foo-bar"), CONSTITUTION)


def test_duplicate_declare_raises() -> None:
    with pytest.raises(ValueError, match="duplicate name 'Foo'"):
        parse_task(_task_text(declares="- Foo\n- Foo"), CONSTITUTION)


def test_declare_with_underscore_accepted() -> None:
    declares = "- foo_bar"
    interfaces = "```python\nclass foo_bar: pass\n```"
    gherkins = (
        "## foo_bar: works\n"
        "```gherkin\n"
        "Given a foo_bar\n"
        "When I call it\n"
        "Then it works\n"
        "```"
    )
    task = parse_task(
        _task_text(
            declares=declares,
            interfaces=interfaces,
            gherkins=gherkins,
        ),
        CONSTITUTION,
    )
    assert task.declares[0].name == "foo_bar"


def test_declare_with_digits_accepted() -> None:
    declares = "- Foo2"
    interfaces = "```python\nclass Foo2: pass\n```"
    gherkins = (
        "## Foo2: works\n```gherkin\nGiven a Foo2\nWhen I call it\nThen it works\n```"
    )
    task = parse_task(
        _task_text(
            declares=declares,
            interfaces=interfaces,
            gherkins=gherkins,
        ),
        CONSTITUTION,
    )
    assert task.declares[0].name == "Foo2"


def test_def_must_be_at_start_of_line() -> None:
    # `class Foo` appearing mid-line (after `x = 1  #`) is not matched by
    # `_FENCE_DEF`, which requires `(?:^|\n)\s*` before `def`/`class`.
    # NOTE: we deliberately do NOT use a line that *starts* with `# ` here —
    # `_SECTION` would treat that as a new section header and truncate the
    # Interfaces section entirely.
    interfaces = "```python\nx = 1  # class Foo: pass\n```"
    with pytest.raises(ValueError, match="cannot find"):
        parse_task(_task_text(interfaces=interfaces), CONSTITUTION)


def test_multiple_declares_parsed() -> None:
    declares = "- Foo\n- Bar"
    interfaces = "```python\nclass Foo: pass\n```\n```python\nclass Bar: pass\n```"
    task = parse_task(
        _task_text(declares=declares, interfaces=interfaces),
        CONSTITUTION,
    )
    assert [d.name for d in task.declares] == ["Foo", "Bar"]


# ---- interfaces: structure ----


def test_no_interfaces_raises() -> None:
    with pytest.raises(ValueError, match="no interfaces declared"):
        parse_task(_task_text(interfaces=""), CONSTITUTION)


def test_interface_fence_without_language_not_matched() -> None:
    # ` ```python ` requires a word right after the backticks; a bare
    # fence has no language and is not counted.
    interfaces = "```\nclass Foo: pass\n```"
    with pytest.raises(ValueError, match="no interfaces declared"):
        parse_task(_task_text(interfaces=interfaces), CONSTITUTION)


def test_count_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="2 declarations but 1 interface fences"):
        parse_task(
            _task_text(
                declares="- Foo\n- Bar",
                interfaces="```python\nclass Foo: pass\n```",
            ),
            CONSTITUTION,
        )


def test_empty_interface_content_raises() -> None:
    with pytest.raises(ValueError, match="interface fence: content is empty"):
        parse_task(
            _task_text(interfaces="```python\n\n```"),
            CONSTITUTION,
        )


def test_interface_without_def_or_class_or_const_raises() -> None:
    with pytest.raises(ValueError, match="cannot find"):
        parse_task(
            _task_text(interfaces="```python\nfoo bar baz\n```"),
            CONSTITUTION,
        )


def test_interface_name_not_in_declares_raises() -> None:
    with pytest.raises(ValueError, match="'Bar' which is not listed in '# Declares'"):
        parse_task(
            _task_text(interfaces="```python\nclass Bar: pass\n```"),
            CONSTITUTION,
        )


def test_duplicate_interface_definition_raises() -> None:
    with pytest.raises(ValueError, match="duplicate definition 'Foo'"):
        parse_task(
            _task_text(
                declares="- Foo\n- Bar",
                interfaces=(
                    "```python\nclass Foo: pass\n```\n```python\nclass Foo: pass\n```"
                ),
            ),
            CONSTITUTION,
        )


# ---- interfaces: name extraction ----


def test_async_def_matched() -> None:
    interfaces = "```python\nasync def Foo():\n    pass\n```"
    task = parse_task(_task_text(interfaces=interfaces), CONSTITUTION)
    assert task.interfaces[0].name == "Foo"


def test_const_only_interface() -> None:
    interfaces = "```python\nFoo: int = 1\n```"
    task = parse_task(_task_text(interfaces=interfaces), CONSTITUTION)
    assert task.interfaces[0].name == "Foo"


def test_def_takes_precedence_over_const() -> None:
    # Both a def and a const are present, but `class Foo` is checked first.
    interfaces = "```python\nOther: int = 1\nclass Foo:\n    pass\n```"
    task = parse_task(_task_text(interfaces=interfaces), CONSTITUTION)
    assert task.interfaces[0].name == "Foo"


def test_language_lowercased() -> None:
    interfaces = "```Python\nclass Foo: pass\n```"
    task = parse_task(_task_text(interfaces=interfaces), CONSTITUTION)
    assert task.interfaces[0].language == "python"


def test_language_with_digit() -> None:
    interfaces = "```python3\nclass Foo: pass\n```"
    task = parse_task(_task_text(interfaces=interfaces), CONSTITUTION)
    assert task.interfaces[0].language == "python3"


# ---- interfaces: description ----


def test_interface_with_description() -> None:
    interfaces = (
        "```python\n"
        "class Foo:\n"
        "    Description:\n"
        "        does things\n"
        "        and more\n"
        "```"
    )
    task = parse_task(_task_text(interfaces=interfaces), CONSTITUTION)
    assert task.interfaces[0].description == "does things and more"


def test_interface_without_description_yields_empty_string() -> None:
    task = parse_task(_task_text(), CONSTITUTION)
    assert task.interfaces[0].description == ""


def test_description_on_same_line_is_ignored() -> None:
    # `Description: inline text` doesn't match — the body must start on
    # the next line and be indented.
    interfaces = "```python\nclass Foo:\n    Description: inline text\n```"
    task = parse_task(_task_text(interfaces=interfaces), CONSTITUTION)
    assert task.interfaces[0].description == ""


def test_description_stops_at_blank_line() -> None:
    # A blank line breaks the `[ \t]+\S.*` capture.
    interfaces = (
        "```python\nclass Foo:\n    Description:\n        first\n\n        ignored\n```"
    )
    task = parse_task(_task_text(interfaces=interfaces), CONSTITUTION)
    assert task.interfaces[0].description == "first"


# ---- interfaces: steps ----


def test_interface_with_steps() -> None:
    interfaces = (
        "```python\n"
        "class Foo:\n"
        "    Steps:\n"
        "        1. step one\n"
        "        2. step two\n"
        "```"
    )
    task = parse_task(_task_text(interfaces=interfaces), CONSTITUTION)
    assert task.interfaces[0].steps == ["step one", "step two"]


def test_interface_without_steps_yields_empty_list() -> None:
    task = parse_task(_task_text(), CONSTITUTION)
    assert task.interfaces[0].steps == []


def test_unindented_steps_lines_ignored() -> None:
    # A line without the `<num>.` prefix ends the `_STEPS` capture.
    interfaces = (
        "```python\nclass Foo:\n    Steps:\n        1. step one\n    not a step\n```"
    )
    task = parse_task(_task_text(interfaces=interfaces), CONSTITUTION)
    assert task.interfaces[0].steps == ["step one"]


def test_multiple_interfaces_parsed() -> None:
    declares = "- Foo\n- Bar"
    interfaces = "```python\nclass Foo: pass\n```\n```python\nclass Bar: pass\n```"
    task = parse_task(
        _task_text(declares=declares, interfaces=interfaces),
        CONSTITUTION,
    )
    assert [i.name for i in task.interfaces] == ["Foo", "Bar"]


# ---- gherkins ----


def test_empty_gherkins_raises() -> None:
    with pytest.raises(ValueError, match="no gherkins declared"):
        parse_task(_task_text(gherkins=""), CONSTITUTION)


def test_gherkin_target_not_in_declares_raises() -> None:
    gherkins = "## Unknown: something\n```gherkin\nGiven g\nWhen w\nThen t\n```"
    with pytest.raises(ValueError, match="'Unknown' is not in '# Declares'"):
        parse_task(_task_text(gherkins=gherkins), CONSTITUTION)


def test_gherkin_missing_fence_raises() -> None:
    gherkins = "## Foo: my test\nNothing here"
    with pytest.raises(ValueError, match="missing ```gherkin``` block"):
        parse_task(_task_text(gherkins=gherkins), CONSTITUTION)


def test_gherkin_fence_is_case_sensitive() -> None:
    gherkins = "## Foo: my test\n```Gherkin\nGiven g\nWhen w\nThen t\n```"
    with pytest.raises(ValueError, match="missing ```gherkin``` block"):
        parse_task(_task_text(gherkins=gherkins), CONSTITUTION)


def test_gherkin_missing_given_raises() -> None:
    gherkins = "## Foo: my test\n```gherkin\nWhen w\nThen t\n```"
    with pytest.raises(ValueError, match="no Given step"):
        parse_task(_task_text(gherkins=gherkins), CONSTITUTION)


def test_gherkin_missing_when_raises() -> None:
    gherkins = "## Foo: my test\n```gherkin\nGiven g\nThen t\n```"
    with pytest.raises(ValueError, match="no When step"):
        parse_task(_task_text(gherkins=gherkins), CONSTITUTION)


def test_gherkin_missing_then_raises() -> None:
    gherkins = "## Foo: my test\n```gherkin\nGiven g\nWhen w\n```"
    with pytest.raises(ValueError, match="no Then step"):
        parse_task(_task_text(gherkins=gherkins), CONSTITUTION)


def test_gherkin_and_without_preceding_raises() -> None:
    gherkins = "## Foo: my test\n```gherkin\nAnd orphan\n```"
    with pytest.raises(ValueError, match="'And' without preceding"):
        parse_task(_task_text(gherkins=gherkins), CONSTITUTION)


def test_gherkin_and_appends_to_current_section() -> None:
    gherkins = (
        "## Foo: my test\n"
        "```gherkin\n"
        "Given g1\n"
        "And g2\n"
        "When w\n"
        "And w2\n"
        "Then t\n"
        "And t2\n"
        "```"
    )
    task = parse_task(_task_text(gherkins=gherkins), CONSTITUTION)
    assert task.gherkins[0].given == ["g1", "g2"]
    assert task.gherkins[0].when == ["w", "w2"]
    assert task.gherkins[0].then == ["t", "t2"]


def test_gherkin_line_without_keyword_raises() -> None:
    gherkins = "## Foo: my test\n```gherkin\nGiven g\nbogus line\nWhen w\nThen t\n```"
    with pytest.raises(ValueError, match="line without keyword"):
        parse_task(_task_text(gherkins=gherkins), CONSTITUTION)


def test_duplicate_gherkin_name_raises() -> None:
    gherkins = (
        "## Foo: dup\n```gherkin\nGiven g\nWhen w\nThen t\n```\n"
        "## Foo: dup\n```gherkin\nGiven g\nWhen w\nThen t\n```"
    )
    with pytest.raises(ValueError, match="duplicate name 'dup'"):
        parse_task(_task_text(gherkins=gherkins), CONSTITUTION)


def test_multiple_gherkins_parsed_in_order() -> None:
    gherkins = (
        "## Foo: first\n```gherkin\nGiven a\nWhen b\nThen c\n```\n"
        "## Foo: second\n```gherkin\nGiven d\nWhen e\nThen f\n```"
    )
    task = parse_task(_task_text(gherkins=gherkins), CONSTITUTION)
    assert [g.name for g in task.gherkins] == ["first", "second"]


# ---- sequence ----


def test_sequence_absent_yields_none() -> None:
    task = parse_task(_task_text(), CONSTITUTION)
    assert task.sequence is None


def test_sequence_mermaid_parsed() -> None:
    sequence = "```mermaid\ngraph LR\nA --> B\n```"
    task = parse_task(_task_text(sequence=sequence), CONSTITUTION)
    assert task.sequence is not None
    assert task.sequence.language == "mermaid"
    assert task.sequence.content == "graph LR\nA --> B"


def test_sequence_plantuml_parsed() -> None:
    sequence = "```plantuml\n@startuml\nA -> B\n@enduml\n```"
    task = parse_task(_task_text(sequence=sequence), CONSTITUTION)
    assert task.sequence is not None
    assert task.sequence.language == "plantuml"
    assert task.sequence.content == "@startuml\nA -> B\n@enduml"


def test_sequence_mermaid_takes_precedence_over_plantuml() -> None:
    sequence = "```mermaid\ngraph LR\nA\n```\n```plantuml\n@startuml\nB\n@enduml\n```"
    task = parse_task(_task_text(sequence=sequence), CONSTITUTION)
    assert task.sequence is not None
    assert task.sequence.language == "mermaid"
    assert task.sequence.content == "graph LR\nA"


def test_sequence_empty_mermaid_raises() -> None:
    sequence = "```mermaid\n\n```"
    with pytest.raises(ValueError, match="mermaid content is empty"):
        parse_task(_task_text(sequence=sequence), CONSTITUTION)


def test_sequence_empty_plantuml_raises() -> None:
    sequence = "```plantuml\n\n```"
    with pytest.raises(ValueError, match="plantuml content is empty"):
        parse_task(_task_text(sequence=sequence), CONSTITUTION)


def test_sequence_no_fence_raises() -> None:
    with pytest.raises(ValueError, match="no ```mermaid``` or ```plantuml``` block"):
        parse_task(_task_text(sequence="just text"), CONSTITUTION)


def test_sequence_fence_is_case_sensitive() -> None:
    sequence = "```Mermaid\ngraph LR\nA\n```"
    with pytest.raises(ValueError, match="no ```mermaid``` or ```plantuml``` block"):
        parse_task(_task_text(sequence=sequence), CONSTITUTION)


# ---- overall shape ----


def test_returns_task_dataclass_with_all_fields() -> None:
    task = parse_task(_task_text(), CONSTITUTION)
    assert isinstance(task, Task)
    assert task.task_id == "t1"
    assert task.target_file == "src/foo.py"
    assert task.target_test_file == "src/foo_test.py"
    assert task.goal == "Build foo."
    assert task.constitution == CONSTITUTION
    assert [d.name for d in task.declares] == ["Foo"]
    assert isinstance(task.interfaces[0], Interface)
    assert isinstance(task.gherkins[0], Gherkin)
    assert task.sequence is None


def test_returns_task_with_sequence_when_present() -> None:
    task = parse_task(
        _task_text(sequence="```mermaid\ngraph LR\nA\n```"),
        CONSTITUTION,
    )
    assert isinstance(task.sequence, Sequence)
