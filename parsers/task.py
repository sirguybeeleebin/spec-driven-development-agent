# parsers/task.py

from __future__ import annotations

import re

from models import Interface, Scenario, Task

_SECTION = re.compile(r"^# (?!#)([^\n]+)$", re.MULTILINE)
_SCENARIO_HEAD = re.compile(r"^## (?!#)([^\n]+)$", re.MULTILINE)
_HEADER_FIELD = re.compile(r"^\s*-\s*(\w+):\s*(.+)$", re.MULTILINE)
_PY_FENCE = re.compile(r"```python\n(.*?)\n```", re.DOTALL)
_GHERKIN_FENCE = re.compile(r"```gherkin\n(.*?)\n```", re.DOTALL)
_MERMAID_FENCE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
_GHERKIN_LINE = re.compile(r"^(Given|When|Then|And)\s+(.+)$")
_SYMBOL = re.compile(
    r"^\s*(?:(?:async\s+)?def|class)\s+(\w+)",
    re.MULTILINE,
)


def parse_task(task: str) -> Task:
    sections: dict[str, str] = {}
    section_matches = list(_SECTION.finditer(task))
    for i, match in enumerate(section_matches):
        name = match.group(1).strip()
        start = match.end()
        end = (
            section_matches[i + 1].start()
            if i + 1 < len(section_matches)
            else len(task)
        )
        sections[name] = task[start:end]

    for required in ("Task", "Goal", "Interfaces", "Scenarios"):
        if required not in sections:
            raise ValueError(f"missing '# {required}' section")

    header: dict[str, str] = {}
    for match in _HEADER_FIELD.finditer(sections["Task"]):
        header[match.group(1)] = match.group(2).strip()
    for key in ("task_id", "target", "target_test"):
        if key not in header:
            raise ValueError(f"task: missing {key}")

    goal = sections["Goal"].strip()

    interfaces: list[Interface] = []
    for fence in _PY_FENCE.finditer(sections["Interfaces"]):
        content = fence.group(1)
        symbol = _SYMBOL.search(content)
        if symbol is None:
            raise ValueError("interface has no class or def")
        interfaces.append(Interface(name=symbol.group(1), content=content))

    scenarios: list[Scenario] = []
    scenario_body = sections["Scenarios"]
    scenario_matches = list(_SCENARIO_HEAD.finditer(scenario_body))
    for i, match in enumerate(scenario_matches):
        name = match.group(1).strip()
        start = match.end()
        end = (
            scenario_matches[i + 1].start()
            if i + 1 < len(scenario_matches)
            else len(scenario_body)
        )
        fence = _GHERKIN_FENCE.search(scenario_body[start:end])
        if fence is None:
            raise ValueError(f"scenario {name!r} missing ```gherkin``` block")
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
                raise ValueError(f"scenario {name!r} line without keyword: {line!r}")
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
                        f"scenario {name!r} 'And' without preceding keyword"
                    )
                current.append(rest)
        scenarios.append(Scenario(name=name, given=given, when=when, then=then))

    activity: str | None = None
    if "Activity" in sections:
        fence = _MERMAID_FENCE.search(sections["Activity"])
        if fence is None:
            raise ValueError("# Activity section has no ```mermaid``` block")
        activity = fence.group(1).strip()

    sequence: str | None = None
    if "Sequence" in sections:
        fence = _MERMAID_FENCE.search(sections["Sequence"])
        if fence is None:
            raise ValueError("# Sequence section has no ```mermaid``` block")
        sequence = fence.group(1).strip()

    if not interfaces:
        raise ValueError("no interfaces declared")
    if not scenarios:
        raise ValueError("no scenarios declared")

    return Task(
        task_id=header["task_id"],
        goal=goal,
        target=header["target"],
        target_test=header["target_test"],
        interfaces=interfaces,
        scenarios=scenarios,
        activity=activity,
        sequence=sequence,
    )