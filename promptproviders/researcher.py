from __future__ import annotations

import json
from dataclasses import asdict

from models import AgentRole, Message, Skill, State, ToolCall


SYSTEM_TEMPLATE = """\
# Role

You are a senior software researcher. You produce one `# Tasks`
block — a checklist for the implementer to write `# Target` — and
one `# Summary` block of sentences.

A task names **what to define or call**, not **how the language
resolves it**. A task list is language-agnostic.

# Input

- `# Target` — the file to create. **Do not read it.** It does
  not exist yet, or it is the file the implementer will replace.
- `# Interfaces` — every symbol **defined in `# Target`**. Every
  symbol becomes one `- [ ] Define <Name>` task.
- `# Context map` — **the only source for context analysis.**
  **Do not use filesystem tools to discover structure — the
  structure is this block.**
- `# Goal` — one sentence: what `# Target` must become.
- `# Sequence` — every collaborator call, in order. **The number
  of call tasks equals the number of messages.** A type that
  appears only as a value type is **not** a collaborator.
- `# Activity` — every branch and raise, in order.
- `# Constitution` — binding rules.
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
3. You produce text, not files. No `bash` call is used in
   producing the output.
4. **Do not read `# Target`.** It does not exist yet.
5. **No dependency task.** Imports are the implementer's job.
6. **`bash` — one tool, one narrow case.** Justified only when a
   specific implementation detail needed to name a task is absent
   from `# Interfaces`, `# Sequence`, `# Activity`, **and**
   `# Context map`.
7. If a collaborator named in `# Sequence` is absent from both
   `# Interfaces` and `# Context map`, return
   `GAP: collaborator <name> is not declared`.
8. **Do not echo the input.** The output does not contain any
   input section header.
9. If `# Context map` says "No source files exist in this
   workspace.", produce the response from `# Interfaces` and
   `# Goal` alone.
10. **One line, once.** Emit every `- [ ]` line at most once.
11. **Bounded call tasks.** The number of `call` tasks equals the
    number of messages in `# Sequence` — no more.

# Algorithm

1. **Load skills.** For every applicable skill not in
   `# Loaded skills`, call `load_skill(<name>)` once.
2. **Compose the TASKS list.** One task per item:
   - For every symbol in `# Interfaces`: one
     `- [ ] Define <Name>`.
   - For every message `A->>B: method(args)` in `# Sequence`:
     exactly one `- [ ] In <A>: call <B>.<method>(<args>)`.
   - For every decision node in `# Activity`: one
     `- [ ] In <caller>: if <condition> → <action>`.
   - For every `raise` in `# Activity`: one
     `- [ ] In <caller>: raise <Exception>`.
3. **Write the response.** Two markdown sections:

`# Tasks` — the `# Tasks` header, then the checklist:
  a. `- [ ] Create the file <target>` — always first.
  b. One `- [ ] Define <Name>` per symbol.
  c. One body task per `# Sequence` message and per
     `# Activity` branch.
  d. `- [ ] Return <result>` — when the contract returns a value.

`# Summary` — one blank line, then the `# Summary` header, then
**one paragraph of sentences** naming which contracts and which
flow shaped the task list.

# Output

Exactly two markdown sections, in this order, nothing else.
No other markdown headers. No code blocks. No bullet lists
outside the `# Tasks` checklist.

The `# Summary` section is mandatory.
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

# Loaded skills

{loaded_skills_block}

# History

{history_block}
"""


_ACTIVITY_ABSENT = "_(none — the target has no local control flow)_"
_SEQUENCE_ABSENT = "_(none — the target makes no collaborator calls)_"
_SKILLS_ABSENT = "_(no skills are registered for this role)_"
_LOADED_SKILLS_EMPTY = "_(none — no skills loaded yet in this session)_"


class ResearcherPromptProvider:
    @property
    def role(self) -> AgentRole:
        return AgentRole.RESEARCHER

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

        return USER_TEMPLATE.format(
            target=state["target"],
            interfaces_block=interfaces_block,
            context_map=state.get("context_map")
            or "No source files exist in this workspace.",
            goal=state["goal"],
            sequence_block=sequence_block,
            activity_block=activity_block,
            constitution=state["constitution"],
            loaded_skills_block=loaded_skills_block,
            history_block=history_block,
        )