# main.py

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
import yaml

from app import build_agent, load_config, load_constitution, load_task
from fsms import TaskFSM, WorkflowFSM
from models import (
    Agents,
    Skill,
    Task,
    TaskStatus,
    Workflow,
    WorkflowStatus,
)
from parsers import parse_graph, parse_skill, parse_task
from promptproviders import (
    FixerPromptProvider,
    ImplementerPromptProvider,
    ResearcherPromptProvider,
    TesterPromptProvider,
)
from prompts import (
    FIXER_FINAL,
    FIXER_SYSTEM_TEMPLATE,
    FIXER_USER_TEMPLATE,
    IMPLEMENTER_FINAL,
    IMPLEMENTER_SYSTEM_TEMPLATE,
    IMPLEMENTER_USER_TEMPLATE,
    RESEARCHER_FINAL,
    RESEARCHER_SYSTEM_TEMPLATE,
    RESEARCHER_USER_TEMPLATE,
    TESTER_FINAL,
    TESTER_SYSTEM_TEMPLATE,
    TESTER_USER_TEMPLATE,
)
from runners import AgentRunner, TaskRunner, WorkflowRunner
from scheduler import Scheduler
from testrunners import PytestRunner

app = typer.Typer(no_args_is_help=True)
config_app = typer.Typer(no_args_is_help=True, help="Manage config.")
run_app = typer.Typer(no_args_is_help=True, help="Run a task or workflow.")
app.add_typer(config_app, name="config")
app.add_typer(run_app, name="run")


@app.command()
def info() -> None:
    rows = [
        (
            "1",
            "config set <key> <value>",
            "Set a config value",
            "config set max_fix_attempts 5",
        ),
        ("2", "config get <key>", "Show a config value", "config get max_fix_attempts"),
        (
            "3",
            "config delete <key>",
            "Delete a config key",
            "config delete max_fix_attempts",
        ),
        ("4", "config clear", "Remove the config file", "config clear"),
        ("5", "info", "Show this table", "info"),
        ("6", "init", "Scaffold the workspace", "init"),
        ("7", "run task <id>", "Run a single task", "run task 001_products_repository"),
        ("8", "run workflow <id>", "Run a whole workflow", "run workflow end_to_end"),
    ]
    header = ("№", "Command", "Description", "Example")
    widths = [max(len(row[i]) for row in rows + [header]) for i in range(4)]
    typer.echo("  ".join(f"{h:<{w}}" for h, w in zip(header, widths, strict=True)))
    typer.echo("  ".join("-" * w for w in widths))
    for row in rows:
        typer.echo("  ".join(f"{c:<{w}}" for c, w in zip(row, widths, strict=True)))


@app.command()
def init() -> None:
    root = Path.cwd().resolve()
    for name in ("AGENT.md", "AGENT.yaml"):
        p = root / name
        typer.echo(f"exists: {p}" if p.exists() else f"missing: {p}")
    for name in ("skills", "tasks", "workflows"):
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        typer.echo(f"ready: {d}")


@config_app.command("set")
def config_set(key: str, value: str) -> None:
    path = Path.cwd().resolve() / "AGENT.yaml"
    data: dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    data[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    typer.echo(f"{key} = {value}")


@config_app.command("get")
def config_get(key: str) -> None:
    path = Path.cwd().resolve() / "AGENT.yaml"
    data: dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    if key not in data:
        typer.echo(f"{key}: not set", err=True)
        raise typer.Exit(code=1)
    typer.echo(str(data[key]))


@config_app.command("delete")
def config_delete(key: str) -> None:
    path = Path.cwd().resolve() / "AGENT.yaml"
    data: dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    if key not in data:
        typer.echo(f"{key}: not set", err=True)
        raise typer.Exit(code=1)
    del data[key]
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    typer.echo(f"{key}: deleted")


@config_app.command("clear")
def config_clear() -> None:
    target = Path.cwd().resolve() / "AGENT.yaml"
    if target.is_symlink() or target.exists():
        target.unlink()
        typer.echo(f"cleared: {target}")
    else:
        typer.echo(f"nothing to clear: {target}")


@run_app.command("task")
def run_task(task_id: str) -> None:
    root = Path.cwd().resolve()

    try:
        config = load_config(root)
        constitution = load_constitution(root)

        skills: dict[str, Skill] = {}
        skills_dir = root / "skills"
        if skills_dir.is_dir():
            for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
                skill = parse_skill(skill_path.read_text(encoding="utf-8"))
                skills[skill.name] = skill

        task_text = load_task(root, task_id)

        providers = {
            Agents.RESEARCHER: ResearcherPromptProvider(
                system_template=RESEARCHER_SYSTEM_TEMPLATE,
                user_template=RESEARCHER_USER_TEMPLATE,
                final_prompt=RESEARCHER_FINAL,
            ),
            Agents.IMPLEMENTER: ImplementerPromptProvider(
                system_template=IMPLEMENTER_SYSTEM_TEMPLATE,
                user_template=IMPLEMENTER_USER_TEMPLATE,
                final_prompt=IMPLEMENTER_FINAL,
            ),
            Agents.TESTER: TesterPromptProvider(
                system_template=TESTER_SYSTEM_TEMPLATE,
                user_template=TESTER_USER_TEMPLATE,
                final_prompt=TESTER_FINAL,
            ),
            Agents.FIXER: FixerPromptProvider(
                system_template=FIXER_SYSTEM_TEMPLATE,
                user_template=FIXER_USER_TEMPLATE,
                final_prompt=FIXER_FINAL,
            ),
        }

        agents: dict[Agents, AgentRunner] = {}
        for role in Agents:
            agents[role] = build_agent(
                role=role,
                config=config,
                skills=skills,
                root=root,
                providers=providers,
            )

        task_runner = TaskRunner(
            researcher=agents[Agents.RESEARCHER],
            implementer=agents[Agents.IMPLEMENTER],
            tester=agents[Agents.TESTER],
            fixer=agents[Agents.FIXER],
            testrunner=PytestRunner(root=root),
            max_fix_attempts=int(config.get("max_fix_attempts", 3)),
            fsm=TaskFSM(),
        )

        task: Task = parse_task(task_text, constitution=constitution)
        result = task_runner.run(task)
    except (FileNotFoundError, ValueError, KeyError, yaml.YAMLError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"task {result.task_id}: {result.status}")
    if result.status is not TaskStatus.SUCCESS:
        raise typer.Exit(code=1)


@run_app.command("workflow")
def run_workflow(workflow_id: str) -> None:
    root = Path.cwd().resolve()

    try:
        config = load_config(root)
        constitution = load_constitution(root)

        skills: dict[str, Skill] = {}
        skills_dir = root / "skills"
        if skills_dir.is_dir():
            for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
                skill = parse_skill(skill_path.read_text(encoding="utf-8"))
                skills[skill.name] = skill

        workflow_path = (root / "workflows") / f"{workflow_id}.md"
        if not workflow_path.exists():
            raise FileNotFoundError(f"workflow file not found: {workflow_path}")
        workflow_text = workflow_path.read_text(encoding="utf-8")

        providers = {
            Agents.RESEARCHER: ResearcherPromptProvider(
                system_template=RESEARCHER_SYSTEM_TEMPLATE,
                user_template=RESEARCHER_USER_TEMPLATE,
                final_prompt=RESEARCHER_FINAL,
            ),
            Agents.IMPLEMENTER: ImplementerPromptProvider(
                system_template=IMPLEMENTER_SYSTEM_TEMPLATE,
                user_template=IMPLEMENTER_USER_TEMPLATE,
                final_prompt=IMPLEMENTER_FINAL,
            ),
            Agents.TESTER: TesterPromptProvider(
                system_template=TESTER_SYSTEM_TEMPLATE,
                user_template=TESTER_USER_TEMPLATE,
                final_prompt=TESTER_FINAL,
            ),
            Agents.FIXER: FixerPromptProvider(
                system_template=FIXER_SYSTEM_TEMPLATE,
                user_template=FIXER_USER_TEMPLATE,
                final_prompt=FIXER_FINAL,
            ),
        }

        agents: dict[Agents, AgentRunner] = {}
        for role in Agents:
            agents[role] = build_agent(
                role=role,
                config=config,
                skills=skills,
                root=root,
                providers=providers,
            )

        task_runner = TaskRunner(
            researcher=agents[Agents.RESEARCHER],
            implementer=agents[Agents.IMPLEMENTER],
            tester=agents[Agents.TESTER],
            fixer=agents[Agents.FIXER],
            testrunner=PytestRunner(root=root),
            max_fix_attempts=int(config.get("max_fix_attempts", 3)),
            fsm=TaskFSM(),
        )
        workflow_runner = WorkflowRunner(
            task_runner=task_runner,
            scheduler=Scheduler(),
            fsm_factory=WorkflowFSM,
        )

        graph = parse_graph(workflow_text)

        parsed: dict[str, Task] = {}
        for node in graph.nodes:
            task_path = (root / "tasks") / f"{node.task_id}.md"
            if not task_path.exists():
                raise FileNotFoundError(
                    f"task file not found: {task_path} "
                    f"(referenced by workflow node {node.task_id!r})"
                )
            t = parse_task(
                load_task(root, node.task_id),
                constitution=constitution,
            )
            parsed[t.task_id] = t

        tasks_list = list(parsed.values())
        workflow = Workflow(
            graph=graph,
            tasks=tasks_list,
            statuses={t.task_id: WorkflowStatus.IDLE for t in tasks_list},
        )
        workflow_result = workflow_runner.run(workflow)
    except (FileNotFoundError, ValueError, KeyError, yaml.YAMLError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    success = sum(1 for r in workflow_result.results if r.status is TaskStatus.SUCCESS)
    total = len(workflow_result.results)
    error = total - success

    for tr in workflow_result.results:
        typer.echo(f"task {tr.task_id}: {tr.status}")
    typer.echo(f"workflow {workflow_id}: {success}/{total} done, {error} failed")
    if not (total and success == total):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
