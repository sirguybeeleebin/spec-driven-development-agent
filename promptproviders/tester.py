# promptproviders/tester.py

from __future__ import annotations

from models import Skill, State


class TesterPromptProvider:
    def __init__(
        self,
        *,
        system_template: str,
        user_template: str,
        final_prompt: str,
    ) -> None:
        self._system = system_template
        self._user = user_template
        self._final = final_prompt

    def format_system(self, skills: list[Skill]) -> str:
        if not skills:
            return self._system
        lines = "\n".join(f"- `{s.name}`: {s.description}" for s in skills)
        return f"{self._system}\n\n# Skills\n\n{lines}"

    def format_user(self, state: State) -> str:
        if not state.declares:
            declares = "_(none)_"
        else:
            declares = "\n".join(f"- `{d.name}`" for d in state.declares)

        if not state.interfaces:
            interfaces = "_(none)_"
        else:
            interface_parts: list[str] = []
            for i in state.interfaces:
                chunk: list[str] = [
                    f"## Interface: {i.name}",
                    f"Language: {i.language}",
                ]
                if i.description:
                    chunk.append(f"Description: {i.description}")
                if i.steps:
                    steps_text = "\n".join(
                        f"{n}. {s}" for n, s in enumerate(i.steps, 1)
                    )
                    chunk.append(f"Steps:\n{steps_text}")
                chunk.append(f"```{i.language}\n{i.content}\n```")
                interface_parts.append("\n\n".join(chunk))
            interfaces = "\n\n".join(interface_parts)

        if state.sequence is None:
            sequence = "_(none)_"
        else:
            sequence = f"```{state.sequence.language}\n{state.sequence.content}\n```"

        if state.gherkin is None:
            gherkin = "_(none)_"
        else:
            gherkin_lines: list[str] = []
            for step in state.gherkin.given:
                gherkin_lines.append(f"Given {step}")
            for step in state.gherkin.when:
                gherkin_lines.append(f"When {step}")
            for step in state.gherkin.then:
                gherkin_lines.append(f"Then {step}")
            gherkin_body = "\n".join(gherkin_lines)
            gherkin = f"## {state.gherkin.name}\n\n```gherkin\n{gherkin_body}\n```"

        return self._user.format(
            target_test_file=state.target_test_file,
            target_declaration=state.target_declaration or "_(none)_",
            test_function=state.test_function,
            gherkin=gherkin,
            declares=declares,
            interfaces=interfaces,
            sequence=sequence,
            implementer_summary=state.implementer_summary.strip() or "_(none)_",
        )

    @property
    def final_user(self) -> str:
        return self._final
