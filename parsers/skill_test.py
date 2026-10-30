# parsers/skill_test.py

from __future__ import annotations

import pytest

from models import Skill
from parsers.skill import parse_skill

BODY = "Follow these instructions."


# ---- helpers ----


def _text(frontmatter: str, body: str = BODY) -> str:
    """Build a skill document from a raw frontmatter block and body."""
    return f"---\n{frontmatter}\n---\n{body}\n"


def _good(
    name: str = "my-skill",
    description: str = "does things",
    body: str = BODY,
) -> str:
    return _text(
        f"name: {name}\ndescription: {description}",
        body,
    )


# ---- happy paths ----


def test_parses_minimal_skill() -> None:
    skill = parse_skill(_good())
    assert isinstance(skill, Skill)
    assert skill.name == "my-skill"
    assert skill.description == "does things"
    assert skill.content == BODY


def test_extra_frontmatter_keys_ignored() -> None:
    text = _text(
        "name: my-skill\ndescription: d\nextra: stuff\nversion: 1.0",
    )
    skill = parse_skill(text)
    assert skill.name == "my-skill"
    assert skill.description == "d"


def test_colon_without_space_accepted() -> None:
    text = _text("name:my-skill\ndescription:does things")
    skill = parse_skill(text)
    assert skill.name == "my-skill"
    assert skill.description == "does things"


def test_extra_whitespace_in_values_trimmed() -> None:
    text = _text("name:   my-skill   \ndescription:   spaced desc   ")
    skill = parse_skill(text)
    assert skill.name == "my-skill"
    assert skill.description == "spaced desc"


def test_internal_whitespace_in_description_preserved() -> None:
    text = _text("name: my-skill\ndescription: one  two  three")
    skill = parse_skill(text)
    assert skill.description == "one  two  three"


def test_opening_fence_with_trailing_whitespace_accepted() -> None:
    text = "---   \nname: my-skill\ndescription: d\n---\nBody.\n"
    skill = parse_skill(text)
    assert skill.name == "my-skill"


def test_closing_fence_with_trailing_whitespace_accepted() -> None:
    text = "---\nname: my-skill\ndescription: d\n---   \nBody.\n"
    skill = parse_skill(text)
    assert skill.content == "Body."


def test_blank_lines_in_frontmatter_skipped() -> None:
    text = _text("name: my-skill\n\ndescription: d\n")
    skill = parse_skill(text)
    assert skill.name == "my-skill"
    assert skill.description == "d"


def test_content_stripped() -> None:
    text = "---\nname: x\ndescription: d\n---\n\n\n   Body\n\n\n"
    skill = parse_skill(text)
    assert skill.content == "Body"


def test_content_markdown_preserved() -> None:
    body = "# Header\n\nSome **bold** and `code`.\n\n```python\nprint('hi')\n```"
    text = _text("name: my-skill\ndescription: d", body)
    skill = parse_skill(text)
    assert skill.content == body


def test_body_may_contain_hr_fence_on_own_line() -> None:
    # Non-greedy regex stops at the FIRST closing `---` on its own line,
    # so a later `---` in the body is preserved as content.
    text = "---\nname: my-skill\ndescription: d\n---\nintro\n---\noutro\n"
    skill = parse_skill(text)
    assert skill.content == "intro\n---\noutro"


def test_body_may_contain_dashes_on_one_line() -> None:
    body = "Some text with --- dashes --- inside."
    skill = parse_skill(_text("name: my-skill\ndescription: d", body))
    assert skill.content == body


# ---- frontmatter structure errors ----


def test_empty_input_raises() -> None:
    with pytest.raises(ValueError, match="missing frontmatter block"):
        parse_skill("")


def test_no_leading_fence_raises() -> None:
    with pytest.raises(ValueError, match="missing frontmatter block"):
        parse_skill("name: x\ndescription: y\nBody.\n")


def test_unclosed_frontmatter_raises() -> None:
    with pytest.raises(ValueError, match="missing frontmatter block"):
        parse_skill("---\nname: x\ndescription: y\nBody.\n")


def test_opening_fence_with_content_on_same_line_rejected() -> None:
    # `---\s*\n` requires a newline right after the fence line.
    with pytest.raises(ValueError, match="missing frontmatter block"):
        parse_skill("--- name: x\ndescription: y\n---\nBody.\n")


def test_only_first_mermaid_like_fence_is_used() -> None:
    # Locked-in behavior: the parser uses the first closing `---` on its
    # own line and everything after is body — even if the body contains
    # another frontmatter-shaped block.
    text = (
        "---\n"
        "name: my-skill\n"
        "description: d\n"
        "---\n"
        "body starts here\n"
        "---\n"
        "name: not-a-key\n"
        "---\n"
    )
    skill = parse_skill(text)
    assert skill.name == "my-skill"
    assert skill.content == "body starts here\n---\nname: not-a-key\n---"


# ---- missing required fields ----


def test_missing_name_raises() -> None:
    with pytest.raises(ValueError, match="missing 'name'"):
        parse_skill(_text("description: d"))


def test_missing_description_raises() -> None:
    with pytest.raises(ValueError, match="missing 'description'"):
        parse_skill(_text("name: my-skill"))


def test_missing_both_raises_on_name_first() -> None:
    with pytest.raises(ValueError, match="missing 'name'"):
        parse_skill(_text("extra: irrelevant"))


# ---- name validation ----


@pytest.mark.parametrize(
    "name",
    ["a", "abc", "123", "abc-123", "abc-123-xyz", "---", "-a-", "a--b"],
)
def test_valid_names_accepted(name: str) -> None:
    skill = parse_skill(_good(name=name))
    assert skill.name == name


@pytest.mark.parametrize(
    "name",
    ["MySkill", "my_skill", "my.skill", "my/skill", "my skill!", "ABC"],
)
def test_invalid_names_rejected(name: str) -> None:
    with pytest.raises(ValueError, match="name must match"):
        parse_skill(_good(name=name))


def test_name_with_internal_spaces_collapsed() -> None:
    # Whitespace is filtered out before validation, so `my skill` → `myskill`.
    skill = parse_skill(_good(name="my skill"))
    assert skill.name == "myskill"


def test_name_with_tabs_and_newlines_filtered() -> None:
    # Split by `splitlines()`; continuation joins with space; filter then
    # removes all whitespace.
    text = _text("name: my\n\tskill\ndescription: d")
    skill = parse_skill(text)
    assert skill.name == "myskill"


def test_name_error_shows_filtered_and_raw_values() -> None:
    with pytest.raises(ValueError) as exc:
        parse_skill(_good(name="My Skill"))
    msg = str(exc.value)
    assert "name must match" in msg
    assert "MySkill" in msg  # filtered (spaces removed)
    assert "My Skill" in msg  # raw value preserved in message


def test_empty_name_raises() -> None:
    with pytest.raises(ValueError, match="empty name"):
        parse_skill(_text("name:\ndescription: d"))


def test_whitespace_only_name_raises() -> None:
    with pytest.raises(ValueError, match="empty name"):
        parse_skill(_text("name:    \ndescription: d"))


def test_non_printable_only_name_raises() -> None:
    # \x00 and \x01 are non-printable → filtered → empty → error.
    text = "---\nname: \x00\x01\x02\ndescription: d\n---\nBody.\n"
    with pytest.raises(ValueError, match="empty name"):
        parse_skill(text)


def test_name_with_colon_in_value_rejected() -> None:
    # partition stops at the first `:`; the colon in the value survives
    # the filter and fails the `[a-z0-9-]+` regex.
    with pytest.raises(ValueError, match="name must match"):
        parse_skill(_text("name: value: extra\ndescription: d"))


def test_name_with_yaml_style_comment_rejected() -> None:
    # The `#` character survives the filter and fails the regex.
    with pytest.raises(ValueError, match="name must match"):
        parse_skill(_good(name="foo # comment"))


# ---- description validation ----


def test_empty_description_raises() -> None:
    with pytest.raises(ValueError, match="empty description"):
        parse_skill(_text("name: my-skill\ndescription:"))


def test_whitespace_only_description_raises() -> None:
    with pytest.raises(ValueError, match="empty description"):
        parse_skill(_text("name: my-skill\ndescription:    "))


# ---- content validation ----


def test_empty_body_raises() -> None:
    with pytest.raises(ValueError, match="empty body"):
        parse_skill("---\nname: my-skill\ndescription: d\n---\n")


def test_whitespace_only_body_raises() -> None:
    with pytest.raises(ValueError, match="empty body"):
        parse_skill("---\nname: my-skill\ndescription: d\n---\n   \n\n\t\n")


# ---- multi-line frontmatter values ----


def test_multiline_description_indented_joined_with_spaces() -> None:
    text = _text(
        "name: my-skill\ndescription: first line\n  second line\n  third line",
    )
    skill = parse_skill(text)
    assert skill.description == "first line second line third line"


def test_description_on_next_line() -> None:
    text = _text(
        "name: my-skill\ndescription:\n  actual desc here",
    )
    skill = parse_skill(text)
    assert skill.description == "actual desc here"


def test_multiline_name_joined_and_whitespace_filtered() -> None:
    text = _text(
        "name: part1\n  part2\ndescription: d",
    )
    skill = parse_skill(text)
    assert skill.name == "part1part2"


def test_indented_line_with_colon_is_continuation() -> None:
    text = _text(
        "name: my-skill\ndescription: line1\n  line2: with colon",
    )
    skill = parse_skill(text)
    assert skill.description == "line1 line2: with colon"


def test_unindented_line_with_colon_is_new_key() -> None:
    text = _text(
        "name: my-skill\ndescription: line1\nextra: line2",
    )
    skill = parse_skill(text)
    assert skill.description == "line1"


def test_unindented_line_without_colon_is_continuation() -> None:
    # A bare word on its own line becomes part of the previous value
    # (implementation quirk — locked in for regression coverage).
    text = _text(
        "name: part1\npart2\ndescription: d",
    )
    skill = parse_skill(text)
    assert skill.name == "part1part2"


def test_indented_line_before_any_key_is_ignored() -> None:
    text = _text(
        "  ignored line: here\nname: my-skill\ndescription: d",
    )
    skill = parse_skill(text)
    assert skill.name == "my-skill"


def test_value_may_contain_colons() -> None:
    text = _text("name: my-skill\ndescription: see: this")
    skill = parse_skill(text)
    assert skill.description == "see: this"


# ---- return shape ----


def test_returns_skill_dataclass_with_populated_fields() -> None:
    skill = parse_skill(_good())
    assert isinstance(skill, Skill)
    assert isinstance(skill.name, str) and skill.name
    assert isinstance(skill.description, str) and skill.description
    assert isinstance(skill.content, str) and skill.content
