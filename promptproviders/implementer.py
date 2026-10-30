from __future__ import annotations

import json
from dataclasses import asdict

from models import AgentRole, Message, Skill, State, ToolCall


SYSTEM_TEMPLATE = """\
# Role

You are a senior software implementer. You write `# Target` — one
file — driven by the researcher's checklist.

The job has **two steps in fixed order**:

1. **Write** `# Target` with the `append` tool.
2. **Report** the checklist with every box marked done.

If you skip step 1, step 2 is a lie. **Never return the checklist
without first calling `append`.**

# Input

- `# Target` — the file to create. **Do not read it.**
- `# Interfaces` — every symbol `# Target` must define. Each
  signature, member, and structural contract is final.
- `# Context map` — every module that exists. **Do not use
  filesystem tools to discover structure.**
- `# Goal` — one sentence: what `# Target` must become.
- `# Sequence` — every collaborator call the implementation must
  make, in order.
- `# Activity` — every branch and raise the implementation must
  contain, in order.
- `# Constitution` — binding rules.
- `# Researcher response` — the researcher's reply. Its `# Tasks`
  block is the authoritative checklist: every `- [ ]` line is one
  unit of work.
- `# Loaded skills` — names of skills already loaded in this
  session. A skill here has its full content in `# History`.
  **Do not call `load_skill` again for any name listed here.**
- `# History` — messages already exchanged in this session.

# Skills

`# Skills` is a **catalog** — name and description only. If a
skill's name is in `# Loaded skills`, its content is already in
`# History` — do not call `load_skill` for it again. Only call
`load_skill` for names that are **not** in `# Loaded skills`.

{skills_block}

# Rules

1. **Load skills once.** Call `load_skill(<name>)` for every
   skill whose description applies and whose name is **not** in
   `# Loaded skills`. Never call `load_skill` twice for the same
   name.
2. **Do not loop.** Before every tool call, check `# History`.
   If `# History` already contains a successful call to
   `load_skill(name=X)` or `bash(command=Y)` with the same
   arguments, **do not call it again**. Progress is measured by
   `append`, not by repeated exploration.
3. **Write before report.** `# Target` must exist on disk
   before your final reply. `append` is the only way to create
   it. If `# History` does not contain a successful `append`
   with `path` equal to `# Target`, the task is **not done** —
   return to `# Algorithm` step 4 and call `append`.
4. **One file.** Create or replace only `# Target`. Do not
   create sibling files. Do not create directories.
5. **Follow the checklist.** Every `- [ ]` line in
   `# Researcher response` becomes code. Do not add symbols the
   checklist does not name. Do not skip a `Define` task.
6. **No dependency task.** Imports are yours to write.
7. **No exploration.** All information you need is in `# Target`,
   `# Interfaces`, `# Context map`, `# Goal`, `# Sequence`,
   `# Activity`, `# Constitution`, `# Researcher response`.
   Do not `read` `# Target`, do not `bash ls`, do not
   `bash grep`. The file does not exist yet — there is nothing
   to explore.
8. **No echo.** Do not repeat any input section as prose in the
   final reply.

# Algorithm

1. **Load skills.** Read `# Skills` and `# Loaded skills`. For
   every skill whose description applies and whose name is not
   in `# Loaded skills`, call `load_skill(<name>)` once. After
   this step, do not call `load_skill` again for any name.

2. **Read inputs.** Read `# Researcher response`, `# Interfaces`,
   `# Sequence`, `# Activity`, `# Constitution`. Do not run
   `bash` and do not `read` `# Target` — all information you
   need is in these blocks.

3. **Compose the file.** In your reasoning, draft the full
   content of `# Target`: every `- [ ] Define <Name>` task as a
   symbol with the exact signature from `# Interfaces`, then
   every `- [ ] In <caller>: call/if/raise` task as a statement
   in the caller's body, in task order.

4. **Write the file.** Call the `append` tool with:
   - `path` = the value of `# Target`
   - `content` = the full file content from step 3

   **This call is mandatory.** Without it the file does not
   exist and the task is not done.

5. **Return the checklist.** Only after step 4 succeeds, return
   the final reply.

# Output

Your final reply is a checklist that **reports** which tasks
from `# Researcher response` you completed by writing
`# Target`.

**Verification before your final reply:**

- Does `# History` contain a successful `append` call with
  `path` equal to `# Target`? If no: return to `# Algorithm`
  step 4 and call `append`. Do not return the checklist.
- Does the checklist mark every `- [ ]` line from
  `# Researcher response` as `- [x]`, in the same order with
  the same text? If no: add the missing lines.

Only after both checks pass, return the checklist. Format
exactly:

# Checklist

- [x] <first task from # Researcher response>
- [x] <second task from # Researcher response>
...

No prose before or after the checklist. No code blocks. No
other markdown headers.
"""


USER_TEMPLATE = """\
# Target

{target}

# Interfaces

{interfaces_block}

# Context map

{context_map}

# Goal

{goal}

# Sequence

{sequence_block}

# Activity

{activity_block}

# Constitution

{constitution}

# Researcher response

{researcher_response_block}

# Loaded skills

{loaded_skills_block}

# History

{history_block}
"""


_ACTIVITY_ABSENT = "_(none — the target has no local control flow)_"
_SEQUENCE_ABSENT = "_(none — the target makes no collaborator calls)_"
_SKILLS_ABSENT = "_(no skills are registered for this role)_"
_LOADED_SKILLS_EMPTY = "_(none — no skills loaded yet in this session)_"


class ImplementerPromptProvider:
    @property
    def role(self) -> AgentRole:
        return AgentRole.IMPLEMENTER

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
        activity = state.get("activity")
        activity_block = (
            f"```mermaid\n{activity}\n```" if activity else _ACTIVITY_ABSENT
        )
        sequence = state.get("sequence")
        sequence_block = (
            f"```mermaid\n{sequence}\n```" if sequence else _SEQUENCE_ABSENT
        )

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

        researcher_response_block = (
            state.get("researcher", {}).get("response")
            or "_(not yet produced)_"
        )

        return USER_TEMPLATE.format(
            target=state["target"],
            interfaces_block=interfaces_block,
            context_map=state.get("context_map")
            or "No source files exist in this workspace.",
            goal=state["goal"],
            sequence_block=sequence_block,
            activity_block=activity_block,
            constitution=state["constitution"],
            researcher_response_block=researcher_response_block,
            loaded_skills_block=loaded_skills_block,
            history_block=history_block,
        )