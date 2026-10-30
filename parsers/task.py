# parsers/task.py

from __future__ import annotations

import re

from models import Declaration, Gherkin, Interface, Sequence, Task

_SECTION = re.compile(r"^# (?!#)([^\n]+)$", re.MULTILINE)
_GHERKIN_HEAD = re.compile(r"^## (\w+): (.+)$", re.MULTILINE)
_HEADER_SCALAR = re.compile(r"^\s*-\s*(\w+):\s*(.+)$")
_DECLARE_ITEM = re.compile(r"^\s*-\s+(\w+)\s*$")
_LANG_TAG = re.compile(r"```(\w+)\n(.*?)\n```", re.DOTALL)
_GHERKIN_FENCE = re.compile(r"```gherkin\n(.*?)\n```", re.DOTALL)
_MERMAID_FENCE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
_PLANTUML_FENCE = re.compile(r"```plantuml\n(.*?)\n```", re.DOTALL)
_GHERKIN_LINE = re.compile(r"^(Given|When|Then|And)\s+(.+)$")
_DESCRIPTION = re.compile(r"Description:\s*\n((?:[ \t]+\S.*\n?)+)")
_STEPS = re.compile(r"Steps:\s*\n((?:[ \t]+\d+\..*\n?)+)")
_STEP_LINE = re.compile(r"^\d+\.\s+(.+)$")
_FENCE_DEF = re.compile(r"(?:^|\n)\s*(?:async\s+)?(?:def|class)\s+(\w+)\b")
_FENCE_CONST = re.compile(r"(?:^|\n)\s*(\w+)\s*:\s*\w+\s*=")


def parse_task(text: str, constitution: str) -> Task:
    if not constitution:
        raise ValueError("task: constitution is empty")

    section_matches = list(_SECTION.finditer(text))
    sections: dict[str, str] = {}
    for i, match in enumerate(section_matches):
        name = match.group(1).strip()
        start = match.end()
        end = (
            section_matches[i + 1].start()
            if i + 1 < len(section_matches)
            else len(text)
        )
        sections[name] = text[start:end]

    for required in ("Task", "Goal", "Declares", "Interfaces", "Gherkins"):
        if required not in sections:
            raise ValueError(f"missing '# {required}' section")

    header: dict[str, str] = {}
    for raw_line in sections["Task"].splitlines():
        m = _HEADER_SCALAR.match(raw_line)
        if m:
            header[m.group(1)] = m.group(2).strip()

    for key in ("task_id", "target_file", "target_test_file"):
        if key not in header:
            raise ValueError(f"task: missing '{key}'")
        if not header[key]:
            raise ValueError(f"task: '{key}' is empty")

    task_id = header["task_id"]
    target_file = header["target_file"]
    target_test_file = header["target_test_file"]

    declares: list[Declaration] = []
    for raw_line in sections["Declares"].splitlines():
        if not raw_line.strip():
            continue
        m = _DECLARE_ITEM.match(raw_line)
        if m is None:
            raise ValueError(
                f"declares: cannot parse line: {raw_line!r}; expected format '- Name'"
            )
        declares.append(Declaration(name=m.group(1)))

    if not declares:
        raise ValueError("declares: empty '# Declares' section")

    seen_names: set[str] = set()
    for d in declares:
        if d.name in seen_names:
            raise ValueError(f"declares: duplicate name {d.name!r}")
        seen_names.add(d.name)

    goal = sections["Goal"].strip()
    if not goal:
        raise ValueError(f"task {task_id!r}: goal is empty")

    fences = list(_LANG_TAG.finditer(sections["Interfaces"]))
    if not fences:
        raise ValueError("no interfaces declared")
    if len(fences) != len(declares):
        raise ValueError(
            f"declares: {len(declares)} declarations but {len(fences)} interface fences"
        )

    matched: set[str] = set()
    interfaces: list[Interface] = []
    for fence in fences:
        language = fence.group(1).strip().lower()
        content = fence.group(2)
        if not content:
            raise ValueError("interface fence: content is empty")

        def_match = _FENCE_DEF.search(content)
        const_match = _FENCE_CONST.search(content)
        if def_match is not None:
            name = def_match.group(1)
        elif const_match is not None:
            name = const_match.group(1)
        else:
            raise ValueError(
                "interface fence: cannot find 'class <Name>' / "
                "'def <Name>' / '<Name>: Type =' in content"
            )
        if name not in seen_names:
            raise ValueError(
                f"interface fence defines {name!r} which is not listed in '# Declares'"
            )
        if name in matched:
            raise ValueError(f"interface: duplicate definition {name!r}")
        matched.add(name)

        desc_match = _DESCRIPTION.search(content)
        if desc_match is None:
            description = ""
        else:
            description = " ".join(
                line.strip()
                for line in desc_match.group(1).splitlines()
                if line.strip()
            )

        steps_match = _STEPS.search(content)
        steps: list[str] = []
        if steps_match is not None:
            for line in steps_match.group(1).splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                step_match = _STEP_LINE.match(stripped)
                if step_match:
                    steps.append(step_match.group(1).strip())

        interfaces.append(
            Interface(
                name=name,
                language=language,
                content=content,
                description=description,
                steps=steps,
            )
        )

    missing = seen_names - matched
    if missing:
        raise ValueError(f"declares: no interface fence for {sorted(missing)!r}")

    gherkins: list[Gherkin] = []
    gherkins_body = sections["Gherkins"]
    gherkins_matches = list(_GHERKIN_HEAD.finditer(gherkins_body))

    seen_gherkins: set[str] = set()
    for i, match in enumerate(gherkins_matches):
        target_declaration = match.group(1).strip()
        name = match.group(2).strip()
        if not name:
            raise ValueError("gherkin: empty name")
        if name in seen_gherkins:
            raise ValueError(f"gherkin: duplicate name {name!r}")
        seen_gherkins.add(name)

        start = match.end()
        end = (
            gherkins_matches[i + 1].start()
            if i + 1 < len(gherkins_matches)
            else len(gherkins_body)
        )
        body = gherkins_body[start:end]

        if target_declaration not in seen_names:
            raise ValueError(
                f"gherkin {name!r} target declaration "
                f"{target_declaration!r} is not in '# Declares'"
            )

        fence = _GHERKIN_FENCE.search(body)
        if fence is None:
            raise ValueError(f"gherkin {name!r} missing ```gherkin``` block")

        given: list[str] = []
        when: list[str] = []
        then: list[str] = []
        current: list[str] | None = None
        for raw_line in fence.group(1).splitlines():
            line = raw_line.strip()
            if not line:
                continue
            step_match = _GHERKIN_LINE.match(line)
            if step_match is None:
                raise ValueError(f"gherkin {name!r} line without keyword: {line!r}")
            keyword = step_match.group(1)
            rest = step_match.group(2)
            if keyword == "Given":
                current = given
                given.append(rest)
            elif keyword == "When":
                current = when
                when.append(rest)
            elif keyword == "Then":
                current = then
                then.append(rest)
            elif keyword == "And":
                if current is None:
                    raise ValueError(
                        f"gherkin {name!r} 'And' without preceding keyword"
                    )
                current.append(rest)

        if not given:
            raise ValueError(f"gherkin {name!r} has no Given step")
        if not when:
            raise ValueError(f"gherkin {name!r} has no When step")
        if not then:
            raise ValueError(f"gherkin {name!r} has no Then step")

        gherkins.append(
            Gherkin(
                name=name,
                target_declaration=target_declaration,
                given=given,
                when=when,
                then=then,
            )
        )

    if not gherkins:
        raise ValueError("no gherkins declared")

    sequence: Sequence | None = None
    if "Sequence" in sections:
        mermaid = _MERMAID_FENCE.search(sections["Sequence"])
        plantuml = _PLANTUML_FENCE.search(sections["Sequence"])
        if mermaid is not None:
            content = mermaid.group(1).strip()
            if not content:
                raise ValueError("sequence: mermaid content is empty")
            sequence = Sequence(language="mermaid", content=content)
        elif plantuml is not None:
            content = plantuml.group(1).strip()
            if not content:
                raise ValueError("sequence: plantuml content is empty")
            sequence = Sequence(language="plantuml", content=content)
        else:
            raise ValueError(
                "# Sequence section has no ```mermaid``` or ```plantuml``` block"
            )

    return Task(
        task_id=task_id,
        goal=goal,
        target_file=target_file,
        target_test_file=target_test_file,
        declares=declares,
        interfaces=interfaces,
        gherkins=gherkins,
        constitution=constitution,
        sequence=sequence,
    )
