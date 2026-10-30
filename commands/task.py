# commands/task.py

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI

from agent import Agent
from hooks import (
    EnsureInitPyPostHook,
    PathWriteGuardPreHook,
    RepeatedReadPreHook,
    RepeatedWritePreHook,
    SkillDedupPreHook,
    SkillRequiredPreHook,
    StopAfterWritePostHook,
)
from llm import LLMClient
from models import Skill, TaskResult, Tools
from parsers import parse_skill, parse_task
from promptproviders import (
    FixerPromptProvider,
    ImplementerPromptProvider,
    ResearcherPromptProvider,
    TesterPromptProvider,
)
from repomap import RepoMap
from repomap.parsers import PythonParser
from runners import TaskRunner
from testrunners import PytestRunner
from tools import AppendTool, BashTool, LoadSkillTool, PatchTool, ReadTool
from validators import validate_skill, validate_task


class RunTaskCommand:
    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()

    def execute(self, task_id: str) -> TaskResult:
        agent_yaml = self._root / "AGENT.yaml"
        config: dict[str, Any] = {}
        if agent_yaml.exists():
            with agent_yaml.open("r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

        repomap = RepoMap(
            parser=PythonParser(),
            root=self._root,
            max_tokens=int(config["repomap"]["max_tokens"]),
        )

        all_skills: dict[str, Skill] = {}
        skills_dir = self._root / "skills"
        if skills_dir.is_dir():
            for p in sorted(skills_dir.glob("*/SKILL.md")):
                skill = parse_skill(p.read_text(encoding="utf-8"))
                validate_skill(skill)
                all_skills[skill.name] = skill

        task_path = (self._root / "tasks") / f"{task_id}.md"
        if not task_path.exists():
            raise FileNotFoundError(f"task file not found: {task_path}")
        task = parse_task(task_path.read_text(encoding="utf-8"))
        validate_task(task)

        def llm(role: str) -> LLMClient:
            p = config["agents"][role]["provider"]
            return LLMClient(
                client=OpenAI(
                    base_url=p["base_url"],
                    api_key=p["api_key"],
                ),
                model=p["model"],
                opts={"temperature": float(p["temperature"])},
            )

        def role_skills(role: str) -> list[Skill]:
            names = config["agents"][role].get("skills", [])
            missing = [n for n in names if n not in all_skills]
            if missing:
                raise ValueError(f"skills not found: {missing}")
            return [all_skills[n] for n in names]

        def tools(role: str, skills: list[Skill]) -> list[Any]:
            result: list[Any] = []
            for tn in config["agents"][role].get("tools", []):
                if tn == Tools.LOAD_SKILL:
                    if not skills:
                        raise ValueError(
                            f"role {role!r} uses 'load_skill' but has no skills"
                        )
                    result.append(LoadSkillTool(skills=skills))
                elif tn == Tools.APPEND:
                    result.append(AppendTool(root=self._root))
                elif tn == Tools.PATCH:
                    result.append(PatchTool(root=self._root))
                elif tn == Tools.READ:
                    result.append(ReadTool(root=self._root))
                elif tn == Tools.BASH:
                    result.append(BashTool(root=self._root))
                else:
                    raise ValueError(f"unknown tool: {tn!r}")
            return result

        def max_iterations(role: str) -> int:
            return int(config["agents"][role].get("max_iterations", 15))

        researcher_skills = role_skills("researcher")
        researcher = Agent(
            llm=llm("researcher"),
            prompt_provider=ResearcherPromptProvider(),
            skills=researcher_skills,
            tools=tools("researcher", researcher_skills),
            pre_hooks=[],
            post_hooks=[],
            max_iterations=max_iterations("researcher"),
        )

        implementer_skills = role_skills("implementer")
        implementer = Agent(
            llm=llm("implementer"),
            prompt_provider=ImplementerPromptProvider(),
            skills=implementer_skills,
            tools=tools("implementer", implementer_skills),
            pre_hooks=[
                SkillRequiredPreHook(skills=implementer_skills),
                SkillDedupPreHook(),
                PathWriteGuardPreHook(),
                RepeatedReadPreHook(),
                RepeatedWritePreHook(),
            ],
            post_hooks=[
                EnsureInitPyPostHook(root=self._root),
                StopAfterWritePostHook(),
            ],
            max_iterations=max_iterations("implementer"),
        )

        tester_skills = role_skills("tester")
        tester = Agent(
            llm=llm("tester"),
            prompt_provider=TesterPromptProvider(),
            skills=tester_skills,
            tools=tools("tester", tester_skills),
            pre_hooks=[
                SkillRequiredPreHook(skills=tester_skills),
                SkillDedupPreHook(),
                PathWriteGuardPreHook(),
                RepeatedWritePreHook(),
            ],
            post_hooks=[
                EnsureInitPyPostHook(root=self._root),
                StopAfterWritePostHook(),
            ],
            max_iterations=max_iterations("tester"),
        )

        fixer_skills = role_skills("fixer")
        fixer = Agent(
            llm=llm("fixer"),
            prompt_provider=FixerPromptProvider(),
            skills=fixer_skills,
            tools=tools("fixer", fixer_skills),
            pre_hooks=[
                SkillRequiredPreHook(skills=fixer_skills),
                SkillDedupPreHook(),
                PathWriteGuardPreHook(),
                RepeatedReadPreHook(),
                RepeatedWritePreHook(),
            ],
            post_hooks=[
                EnsureInitPyPostHook(root=self._root),
                StopAfterWritePostHook(),
            ],
            max_iterations=max_iterations("fixer"),
        )

        task_runner = TaskRunner(
            repomap=repomap,
            researcher=researcher,
            implementer=implementer,
            tester=tester,
            fixer=fixer,
            testrunner=PytestRunner(root=self._root),
            max_fix_attempts=int(config.get("max_fix_attempts", 3)),
        )

        return task_runner.run(task)