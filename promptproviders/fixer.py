from __future__ import annotations

import json
from dataclasses import asdict

from models import AgentRole, Message, Skill, State, ToolCall


SYSTEM_TEMPLATE = """\
# Role

You are a senior software fixer. You receive a failing test, its
output, and the current sources. You produce the smallest patch
that makes `# Test function` pass.

**Both files exist.** Implementer created `# Target`, tester
created `# Target test`. Your job is to patch one or both —
never to create them.

# Input

- `# Target` — the file under test. Exists.
- `# Target test` — the test file. Exists.
- `# Interfaces` — every symbol `# Target` defines.
- `# Context map` — every module that exists.
- `# Scenario` — the Given / When / Then the failing test
  encodes.
- `# Test function` — exact function name pytest reports on.
- `# Current test source` — current content of `# Target test`.
- `# Test output` — the pytest failure output.
- `# Constitution` — binding rules for both files.
- `# Tester response` — the tester's reply.
- `# Loaded skills` — names of skills already loaded in this
  session. A skill here has its full content in `# History`.
  **Do not call `load_skill` again for any name listed here.**
- `# History` — messages already exchanged in this session.

# Skills

`# Skills` is a **catalog** — name and description only. If a
skill's name is in `# Loaded skills`, its content is already in
`# History` — do not call `load_skill` for it again.

{skills_block}

# Rules

1. **Load skills once.** Call `load_skill(<name>)` for every
   skill whose description applies and whose name is **not** in
   `# Loaded skills`. Never call `load_skill` twice for the same
   name.
2. **Do not loop.** Before every tool call, check `# History`.
   If `# History` already contains a successful call to
   `load_skill(name=X)` or `bash(command=Y)` with the same
   arguments, do not call it again.
3. **Patch existing files only.** `# Target` and `# Target test`
   exist. If `patch` returns `error: ... file not found`, the
   file was not created upstream — this is **not** your
   responsibility. **Do not retry. Do not `bash find`. Do not
   `bash ls`. Do not call `patch` on any other path.** Produce
   the final message reporting the upstream failure and stop.
4. **Address the actual failure.** `# Test output` names the
   assertion or exception. Do not rewrite unrelated code.
5. **Smallest patch.** Change only what the failure requires.
6. **Two files, no more.** Patch `# Target`, `# Target test`,
   or both.
7. **Do not rename.** `# Test function` is fixed by pytest.
   Symbol names in `# Interfaces` are fixed.
8. **No exploration.** Everything needed is in the input. Do not
   `read`, do not `ls`, do not `grep`.

# Algorithm

1. **Load skills.** For every applicable skill not in
   `# Loaded skills`, call `load_skill(<name>)` once.
2. Read `# Test output`. Identify the failing assertion or
   exception.
3. Read `# Current test source`. Identify the line(s) that
   produced it.
4. Read `# Tester response` and `# Scenario`. Check the test
   correctly encodes Given / When / Then. If not, the fix is in
   `# Target test`.
5. Read `# Interfaces`. Check the target correctly implements
   the symbol named in the failure. If not, the fix is in
   `# Target`.
6. **Apply the smallest patch.** Call `patch` with `path` equal
   to whichever file the fix is in.
7. **Return one sentence** naming the failure and the change.

**If step 6 fails with `file not found`:** do not retry, do not
search. Produce the final message reporting that `# Target` or
`# Target test` does not exist — the fixer cannot create it.

# Output

One short paragraph naming the failure and the change.

**Verification before your final reply:**

- Did step 6 succeed with a `patch` call? If yes: return the
  paragraph.
- Did step 6 fail with `file not found`? Return a paragraph
  reporting the upstream failure — `# Target` or `# Target test`
  does not exist, the fixer cannot create it.

No markdown headers. No code blocks.
"""


USER_TEMPLATE = """\
# Target

{target}

# Target test

{target_test}

# Interfaces

{interfaces_block}

# Context map

{context_map}

# Scenario

{scenario_block}

# Test function

{test_function}

# Current test source

{test_source_block}

# Test output

{test_output_block}

# Constitution

{constitution}

# Tester response

{tester_response_block}

# Loaded skills

{loaded_skills_block}

# History

{history_block}
"""


_SKILLS_ABSENT = "_(no skills are registered for this role)_"
_LOADED_SKILLS_EMPTY = "_(none — no skills loaded yet in this session)_"


class FixerPromptProvider:
    @property
    def role(self) -> AgentRole:
        return AgentRole.FIXER

    def format_system(self, skills: list[Skill]) -> str:
        skills_block = (
            "\n\n".join(f"## {s.name}\n\n{s.description}" for s in skills)
            or _SKILLS_ABSENT
        )
        return SYSTEM_TEMPLATE.format(skills_block=skills_block)

    @property
    def summary_request(self) -> str:
        return (
            "\n\n# Summary request\n\n"
            "The session reached its stop condition. Do not call any "
            "tool now. Your next reply is the final message per "
            "`# Output`."
        )

    def format_user(self, state: State) -> str:
        interfaces_block = (
            "\n\n".join(
                f"## Interface: {i.name}\n\n{i.content}"
                for i in state["interfaces"]
            )
            or "_(none)_"
        )
        test_source = state.get("test_source") or ""
        test_source_block = (
            f"```python\n{test_source}\n```"
            if test_source
            else "_(empty)_"
        )
        test_output = state.get("test_output") or ""
        test_output_block = (
            f"```\n{test_output}\n```" if test_output else "_(empty)_"
        )

        scenario = state["scenario"]
        scenario_parts = [f"- Name: {scenario.name}"]
        for field in ("given", "when", "then"):
            value = getattr(scenario, field, None)
            if value:
                scenario_parts.append(f"- {field.capitalize()}: {value}")
        scenario_block = "\n".join(scenario_parts)

        session = state.get(self.role) or {}
        history: list[Message] = session.get("history") or []

        loaded: list[str] = []
        pending: dict[str, ToolCall] = {}
        for msg in history:
            if msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    pending[tc.id] = tc
            elif msg.role == "tool":
                tc = pending.pop(msg.tool_call_id, None)
                if tc is None or tc.name != "load_skill":
                    continue
                try:
                    parsed = json.loads(msg.content)
                except (json.JSONDecodeError, TypeError):
                    continue
                if "error" in parsed or "hint" in parsed:
                    continue
                name = tc.arguments.get("name")
                if isinstance(name, str) and name not in loaded:
                    loaded.append(name)

        loaded_skills_block = (
            "\n".join(f"- {n}" for n in loaded)
            or _LOADED_SKILLS_EMPTY
        )
        print(
            f"[prompt.{self.role}] loaded_skills={loaded}",
            flush=True,
        )

        history_block = (
            "\n".join(
                json.dumps(asdict(m), ensure_ascii=True) for m in history
            )
            or "_(empty — first turn of this session)_"
        )

        tester_response_block = (
            state.get("tester", {}).get("response")
            or "_(not yet produced)_"
        )

        return USER_TEMPLATE.format(
            target=state["target"],
            target_test=state["target_test"],
            interfaces_block=interfaces_block,
            context_map=state.get("context_map")
            or "No source files exist in this workspace.",
            scenario_block=scenario_block,
            test_function=state["test_function"],
            test_source_block=test_source_block,
            test_output_block=test_output_block,
            constitution=state["constitution"],
            tester_response_block=tester_response_block,
            loaded_skills_block=loaded_skills_block,
            history_block=history_block,
        )