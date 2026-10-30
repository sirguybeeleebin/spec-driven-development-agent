# main.py

from __future__ import annotations

from pathlib import Path

import typer

from commands import (
    RunConfigClearCommand,
    RunConfigDeleteCommand,
    RunConfigGetCommand,
    RunConfigSetCommand,
    RunInfoCommand,
    RunInitCommand,
    RunTaskCommand,
    RunWorkflowCommand,
)

app = typer.Typer(no_args_is_help=True)
config_app = typer.Typer(no_args_is_help=True, help="Manage config.")
run_app = typer.Typer(no_args_is_help=True, help="Run a task or workflow.")
app.add_typer(config_app, name="config")
app.add_typer(run_app, name="run")


@app.command()
def info() -> None:
    rows = RunInfoCommand().execute()
    header = ("№", "Command", "Description", "Example")
    widths = [max(len(row[i]) for row in rows + [header]) for i in range(4)]
    typer.echo("  ".join(f"{h:<{w}}" for h, w in zip(header, widths, strict=True)))
    typer.echo("  ".join("-" * w for w in widths))
    for row in rows:
        typer.echo("  ".join(f"{c:<{w}}" for c, w in zip(row, widths, strict=True)))


@app.command()
def init() -> None:
    for line in RunInitCommand(root=Path.cwd()).execute():
        typer.echo(line)


@config_app.command("set")
def config_set(key: str, value: str) -> None:
    RunConfigSetCommand(root=Path.cwd()).execute(key, value)
    typer.echo(f"{key} = {value}")


@config_app.command("get")
def config_get(key: str) -> None:
    try:
        value = RunConfigGetCommand(root=Path.cwd()).execute(key)
    except KeyError:
        typer.echo(f"{key}: not set", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(value)


@config_app.command("delete")
def config_delete(key: str) -> None:
    try:
        RunConfigDeleteCommand(root=Path.cwd()).execute(key)
    except KeyError:
        typer.echo(f"{key}: not set", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"{key}: deleted")


@config_app.command("clear")
def config_clear() -> None:
    target = Path.cwd() / "AGENT.yaml"
    existed = target.exists()
    RunConfigClearCommand(root=Path.cwd()).execute()
    if existed:
        typer.echo(f"cleared: {target}")
    else:
        typer.echo(f"nothing to clear: {target}")


@run_app.command("task")
def run_task(task_id: str) -> None:
    try:
        result = RunTaskCommand(root=Path.cwd()).execute(task_id)
    except FileNotFoundError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"task {result.task_id}: {result.status}")
    if not result.ok:
        raise typer.Exit(code=1)


@run_app.command("workflow")
def run_workflow(workflow_id: str) -> None:
    try:
        result = RunWorkflowCommand(root=Path.cwd()).execute(workflow_id)
    except FileNotFoundError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    for tr in result.results:
        typer.echo(f"task {tr.task_id}: {tr.status}")
    total = len(result.results)
    done = sum(1 for tr in result.results if tr.ok)
    failed = total - done
    typer.echo(f"workflow {workflow_id}: {done}/{total} done, {failed} failed")
    if not result.ok:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
