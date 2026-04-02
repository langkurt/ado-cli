"""ado pipelines — build pipeline commands."""
import click
from azure.devops.v7_1.build.models import Build, DefinitionReference

from ado import fmt
from ado.client import ADOClient


@click.group("pipelines")
def pipelines_group():
    """Build pipelines."""


@pipelines_group.command("list")
@click.pass_obj
def pipelines_list(client: ADOClient):
    """List pipeline definitions."""
    defs = client.build.get_definitions(project=client.project)
    fmt.table(
        f"Pipelines · {client.project}",
        ["ID", "Name", "Path", "Queue"],
        [
            [
                d.id,
                d.name,
                d.path or "\\",
                d.queue.name if d.queue else "",
            ]
            for d in defs
        ],
        col_styles=["cyan", "bold", "dim", None],
    )


@pipelines_group.command("runs")
@click.argument("pipeline_id", type=int)
@click.option("--limit", "-n", default=10, show_default=True)
@click.pass_obj
def pipeline_runs(client: ADOClient, pipeline_id: int, limit: int):
    """List recent runs for a pipeline."""
    builds = client.build.get_builds(
        project=client.project,
        definitions=[pipeline_id],
        top=limit,
    )
    fmt.table(
        f"Runs · pipeline {pipeline_id}",
        ["ID", "Status", "Result", "Branch", "Requested By", "Finish Time"],
        [
            [
                b.id,
                _status(b.status),
                _result(b.result),
                (b.source_branch or "").replace("refs/heads/", ""),
                b.requested_by.display_name if b.requested_by else "",
                str(b.finish_time)[:16] if b.finish_time else "—",
            ]
            for b in builds
        ],
        col_styles=["cyan", None, None, "yellow", "dim", "dim"],
    )


@pipelines_group.command("run")
@click.argument("pipeline_id", type=int)
@click.option("--branch", "-b", default="main", show_default=True)
@click.option("--var", "-v", multiple=True, metavar="KEY=VALUE", help="Pipeline variables")
@click.pass_obj
def pipeline_run(client: ADOClient, pipeline_id: int, branch: str, var: tuple):
    """Trigger a pipeline run."""
    variables = {}
    for v in var:
        k, _, val = v.partition("=")
        variables[k] = {"value": val}

    build = client.build.queue_build(
        Build(
            definition=DefinitionReference(id=pipeline_id),
            source_branch=f"refs/heads/{branch}",
            parameters=str(variables) if variables else None,
        ),
        project=client.project,
    )
    fmt.ok(f"Queued run #{build.id} (status: {build.status})")
    fmt.console.print(f"[blue]{build.url}[/blue]")


@pipelines_group.command("show")
@click.argument("run_id", type=int)
@click.pass_obj
def pipeline_show(client: ADOClient, run_id: int):
    """Show details of a specific run."""
    b = client.build.get_build(project=client.project, build_id=run_id)
    if fmt.json_mode:
        fmt.output_json({
            "id": b.id,
            "pipeline": b.definition.name,
            "status": str(b.status),
            "result": str(b.result) if b.result else None,
            "branch": (b.source_branch or "").replace("refs/heads/", ""),
            "trigger": str(b.reason),
            "started": str(b.start_time)[:16] if b.start_time else None,
            "finished": str(b.finish_time)[:16] if b.finish_time else None,
            "url": b.url,
        })
        return
    c = fmt.console
    c.print(f"\n[bold]Run #{b.id}[/bold] · {b.definition.name}")
    c.print(f"[dim]Status:[/dim]   {_status(b.status)}")
    c.print(f"[dim]Result:[/dim]   {_result(b.result)}")
    c.print(f"[dim]Branch:[/dim]   {(b.source_branch or '').replace('refs/heads/', '')}")
    c.print(f"[dim]Trigger:[/dim]  {b.reason}")
    c.print(f"[dim]Started:[/dim]  {str(b.start_time)[:16] if b.start_time else '—'}")
    c.print(f"[dim]Finished:[/dim] {str(b.finish_time)[:16] if b.finish_time else '—'}")
    c.print(f"[blue]{b.url}[/blue]\n")


def _status(s) -> str:
    return {"inProgress": "[yellow]in progress[/yellow]", "completed": "completed",
             "notStarted": "[dim]not started[/dim]", "cancelling": "[red]cancelling[/red]"}.get(str(s), str(s))


def _result(r) -> str:
    return {"succeeded": "[green]succeeded[/green]", "failed": "[red]failed[/red]",
             "canceled": "[dim]canceled[/dim]", "partiallySucceeded": "[yellow]partial[/yellow]"}.get(str(r), str(r) if r else "—")
