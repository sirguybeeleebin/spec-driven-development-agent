# promptproviders/fixer.py

from __future__ import annotations

from models import Skill, State


class FixerPromptProvider:
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
        if state.test_result is None:
            test_result = "_(none)_"
        else:
            status = "passed" if state.test_result.passed else "failed"
            test_result = f"Status: {status}\n```\n{state.test_result.output}\n```"

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

        return self._user.format(
            target_test_file=state.target_test_file,
            target_file=state.target_file,
            test_function=state.test_function,
            test_result=test_result,
            interfaces=interfaces,
            implementer_summary=state.implementer_summary.strip() or "_(none)_",
            tester_summary=state.tester_summary.strip() or "_(none)_",
        )

    @property
    def final_user(self) -> str:
        return self._final
