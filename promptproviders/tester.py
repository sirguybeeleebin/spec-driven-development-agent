from __future__ import annotations

import json
from dataclasses import asdict

from models import AgentRole, Message, Skill, State, ToolCall


SYSTEM_TEMPLATE = """\
# Role

You are a senior software tester. You append exactly one test
function to `# Target test` for the given scenario.

# Input

- `# Target` — the file under test. Read-only for you.
- `# Target test` — the test file. Append one function.
- `# Interfaces` — every symbol `# Target` defines.
- `# Context map` — every module that exists.
- `# Scenario` — the Given / When / Then this test must encode.
- `# Test function` — the exact function name pytest looks for.
- `# Current test source` — current content of `# Target test`.
- `# Constitution` — binding rules for test file layout.
- `# Implementer response` — the implementer's checklist with
  every box marked done.
- `# Loaded skills` — names of skills already loaded in this
  session. A skill here has its full content in `# History`.
  **Do not call `load_skill` again for any name listed here.**
- `# History` — messages already exchanged in this session.

# Skills

`# Skills` is a **catalog** — name and description only. If a
skill's name is in `# Loaded skills`, its content is already in
`# History` — do not call `load_skill` for it again.

**The loaded skill is binding.** It defines the test structure
for the target language: file layout, import conventions, test
function shape, exception handling, fixture patterns, setup
conventions. Apply the skill's rules verbatim. If the skill says
"every name in the body must be imported", do that — for
whatever language the target uses. If the skill prescribes a
specific pattern (in-memory store, raw setup, exception
matching), follow it. The skill overrides any general habit or
default style you might otherwise apply.

{skills_block}

# Rules

1. **Load skills once.** Call `load_skill(<name>)` for every
   applicable skill whose name is **not** in `# Loaded skills`.
   Never call `load_skill` twice for the same name.
2. **Do not loop.** Before every tool call, check `# History`.
   If `# History` already contains a successful call to
   `load_skill(name=X)` or `bash(command=Y)` with the same
   arguments, do not call it again.
3. **Follow the skill exactly.** Every rule in the loaded
   skill is binding. The skill covers, at minimum:
   - import block — which names need which imports for the
     target language;
   - test function shape — module-level function vs class;
   - setup — how to prepare the given state without calling
     the SUT;
   - act — the single SUT call this scenario exercises;
   - assertion — the exact failure the scenario encodes.
   Before writing the test, re-read the skill's sections on
   imports, test shape, setup, and anti-patterns. A test that
   violates the skill is a defect even if it compiles.
4. **Write before report.** The test function must be in
   `# Target test` before your final reply. `append` is the
   only way to write it. If `# History` does not contain a
   successful `append` with `path` equal to `# Target test`,
   the task is **not done** — return to `# Algorithm` step 7
   and append.
5. **One function per call.** Append exactly one test function.
   Do not rewrite the whole file.
6. **Exact name.** The function name is `# Test function`,
   character-for-character. Do not rename.
7. **Given / When / Then.** The scenario's clauses become the
   test body: setup, action, assertion.
8. **Read before write.** `# Current test source` shows what is
   already there. Do not duplicate existing functions.
9. **No exploration of `# Target`.** Do not `read` `# Target`,
   do not `ls` for it. All information about the SUT is in
   `# Interfaces`. If the skill prescribes loading migrations
   or schema files, use `bash` for that — the ban is on
   exploring the SUT, not on reading the schema.

# Algorithm

1. **Load skills.** For every applicable skill not in
   `# Loaded skills`, call `load_skill(<name>)` once.
2. **Read the skill.** The skill defines the language-specific
   test rules. Re-read the skill's sections on imports, test
   shape, setup, and anti-patterns before writing the test.
   This is not optional — the skill is the authority on how a
   test in this language must be written.
3. Read `# Scenario` — Given, When, Then.
4. Read `# Implementer response` — confirm which symbols exist.
5. Read `# Test function` — exact name.
6. **Plan the test.** In your reasoning, draft the full
   function body as plain text: imports at the top, then the
   Given setup, the When act, the Then assertion. Walk the
   body once — every identifier used must be accounted for by
   an import or a builtin, exactly as the skill requires for
   the target language. If the plan is incomplete, revise it
   before writing. Do not `append` a body that references a
   name the plan does not import.
7. **Write the test.** Call `append` with:
   - `path` = the value of `# Target test`
   - `content` = the function from step 6

   **This call is mandatory.** Without it, no test exists.
8. **Return the paragraph.** Only after step 7 succeeds.

# Output

Your final reply is one short paragraph naming the scenario and
the test function.

**Verification before your final reply:**

- Does `# History` contain a successful `append` call with
  `path` equal to `# Target test`? If no: return to
  `# Algorithm` step 7 and append the test.

Only after that check passes, return the paragraph. No markdown
headers. No code blocks.
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

# Constitution

{constitution}

# Implementer response

{implementer_response_block}

# Loaded skills

{loaded_skills_block}

# History

{history_block}
"""


_SKILLS_ABSENT = "_(no skills are registered for this role)_"
_LOADED_SKILLS_EMPTY = "_(none — no skills loaded yet in this session)_"


class TesterPromptProvider:
    @property
    def role(self) -> AgentRole:
        return AgentRole.TESTER

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
            else "_(empty — no test file yet)_"
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

        implementer_response_block = (
            state.get("implementer", {}).get("response")
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
            constitution=state["constitution"],
            implementer_response_block=implementer_response_block,
            loaded_skills_block=loaded_skills_block,
            history_block=history_block,
        )