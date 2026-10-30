# app/factory.py

from __future__ import annotations

from pathlib import Path
from typing import Any

from openai import OpenAI

from hooks import PythonValidationHook
from llm import LLMClient
from models import Agents, Skill, Tools
from runners import AgentRunner
from runners.agent import Hook, PromptProvider
from tools import AppendTool, BashTool, LoadSkillTool, PatchTool, ReadTool


def build_agent(
    *,
    role: Agents,
    config: dict[str, Any],
    skills: dict[str, Skill],
    root: Path,
    providers: dict[Agents, PromptProvider],
    hooks: list[Hook] | None = None,
) -> AgentRunner:
    provider_config = config["agents"][role]["provider"]
    opts: dict[str, Any] = {"temperature": float(provider_config["temperature"])}
    if "max_tokens" in provider_config:
        opts["max_tokens"] = int(provider_config["max_tokens"])
    llm = LLMClient(
        client=OpenAI(
            base_url=provider_config["base_url"],
            api_key=provider_config["api_key"],
        ),
        model=provider_config["model"],
        opts=opts,
    )

    names = config["agents"][role].get("skills", [])
    missing = [n for n in names if n not in skills]
    if missing:
        raise ValueError(f"skills not found: {missing}")
    role_skills = [skills[n] for n in names]

    tool_names = list(config["agents"][role].get("tools", []))
    role_tools: list[Any] = []
    needs_validation_hook = False
    for tn in tool_names:
        if tn == Tools.LOAD_SKILL:
            if not role_skills:
                raise ValueError(
                    f"role {role.value!r} uses 'load_skill' but has no skills"
                )
            role_tools.append(LoadSkillTool(skills=role_skills))
        elif tn == Tools.APPEND:
            role_tools.append(AppendTool(root=root))
            needs_validation_hook = True
        elif tn == Tools.PATCH:
            role_tools.append(PatchTool(root=root))
            needs_validation_hook = True
        elif tn == Tools.READ:
            role_tools.append(ReadTool(root=root))
        elif tn == Tools.BASH:
            role_tools.append(BashTool(root=root))
        else:
            raise ValueError(f"unknown tool: {tn!r}")

    auto_hooks: list[Hook] = []
    if needs_validation_hook:
        auto_hooks.append(PythonValidationHook(root=root))
    combined_hooks: list[Hook] = [*(hooks or []), *auto_hooks]

    max_iterations = int(config["agents"][role].get("max_iterations", 15))

    return AgentRunner(
        llm=llm,
        prompt_provider=providers[role],
        skills=role_skills,
        tools=role_tools,
        hooks=combined_hooks,
        max_iterations=max_iterations,
    )
