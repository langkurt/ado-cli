"""ado status — project status summary: work items, PRs, and pipelines."""
import click
from azure.devops.exceptions import AzureDevOpsServiceError
from azure.devops.v7_1.git.models import GitPullRequestSearchCriteria
from azure.devops.v7_1.work_item_tracking.models import Wiql

from ado import fmt
from ado.client import ADOClient


@click.command("status")
@click.argument("keyword")
@click.option("--area", default=None, help="Area path to scope work items (overrides keyword inference)")
@click.pass_obj
def status_cmd(client: ADOClient, keyword: str, area: str):
    """Show status of a project area: active work items, open PRs, and recent pipeline runs.

    KEYWORD is matched against work item titles, repo names, and pipeline names.

    Examples:
      ado status "Move Metrics"
      ado status "FEC" --area "Gate"
    """
    needle = keyword.lower()
    needle_compact = needle.replace(" ", "")  # "move metrics" → "movemetrics" for repo/pipeline matching

    # ── Work Items ──────────────────────────────────────────────────────────────
    fmt.console.print(f"\n[bold]Work Items[/bold] · matching [cyan]{keyword!r}[/cyan]")
    area_path = area or keyword
    where_parts = [
        f"[System.TeamProject] = '{client.project}'",
        f"[System.Title] CONTAINS '{keyword}'",
        "[System.State] NOT IN ('Closed', 'Resolved', 'Done')",
    ]
    try:
        query = (
            "SELECT [System.Id], [System.Title], [System.WorkItemType], "
            "[System.State], [System.AssignedTo] "
            f"FROM WorkItems WHERE {' AND '.join(where_parts)} "
            "ORDER BY [System.ChangedDate] DESC"
        )
        result = client.work_item_tracking.query_by_wiql(Wiql(query=query))
        refs = (result.work_items or [])[:20]
        if refs:
            ids = [r.id for r in refs]
            items = client.work_item_tracking.get_work_items(ids=ids, error_policy="omit")
            fmt.table(
                None,
                ["ID", "Type", "State", "Assigned To", "Title"],
                [
                    [
                        wi.id,
                        wi.fields.get("System.WorkItemType", ""),
                        wi.fields.get("System.State", ""),
                        _name(wi.fields.get("System.AssignedTo")),
                        wi.fields.get("System.Title", "")[:60],
                    ]
                    for wi in items
                ],
                col_styles=["cyan", "dim", "yellow", "dim", "bold"],
            )
        else:
            fmt.console.print("  [dim]No active work items found.[/dim]")
    except Exception as e:
        fmt.console.print(f"  [red]Error fetching work items: {e}[/red]")

    # ── Open PRs ────────────────────────────────────────────────────────────────
    fmt.console.print(f"\n[bold]Open PRs[/bold] · repos matching [cyan]{keyword!r}[/cyan]")
    try:
        all_repos = client.git.get_repositories(project=client.project)
        matching_repos = [r for r in all_repos if needle in r.name.lower() or needle_compact in r.name.lower().replace(".", "").replace("-", "").replace("_", "")]
        search = GitPullRequestSearchCriteria(status="active")
        pr_rows = []
        for r in matching_repos:
            try:
                prs = client.git.get_pull_requests(r.id, search, project=client.project)
                for pr in prs:
                    pr_rows.append([
                        pr.pull_request_id,
                        r.name,
                        pr.title[:55],
                        pr.created_by.display_name,
                        f"{pr.source_ref_name.replace('refs/heads/', '')} → {pr.target_ref_name.replace('refs/heads/', '')}",
                    ])
            except AzureDevOpsServiceError:
                pass
        if pr_rows:
            fmt.table(None, ["PR", "Repo", "Title", "Author", "Branch"], pr_rows,
                      col_styles=["cyan", "dim", "bold", None, "yellow"])
        else:
            fmt.console.print("  [dim]No open PRs found.[/dim]")
    except Exception as e:
        fmt.console.print(f"  [red]Error fetching PRs: {e}[/red]")

    # ── Recent Pipeline Runs ─────────────────────────────────────────────────────
    fmt.console.print(f"\n[bold]Pipelines[/bold] · matching [cyan]{keyword!r}[/cyan]")
    try:
        all_defs = client.build.get_definitions(project=client.project)
        matching_defs = [d for d in all_defs if needle in d.name.lower() or needle_compact in d.name.lower().replace(".", "").replace("-", "").replace("_", "")]
        pipe_rows = []
        for d in matching_defs:
            builds = client.build.get_builds(project=client.project, definitions=[d.id], top=1)
            if builds:
                b = builds[0]
                pipe_rows.append([
                    d.id,
                    d.name,
                    _status(b.status),
                    _result(b.result),
                    (b.source_branch or "").replace("refs/heads/", ""),
                    str(b.finish_time)[:16] if b.finish_time else "—",
                ])
        if pipe_rows:
            fmt.table(None, ["ID", "Pipeline", "Status", "Result", "Branch", "Finished"],
                      pipe_rows, col_styles=["cyan", "bold", None, None, "yellow", "dim"])
        else:
            fmt.console.print("  [dim]No matching pipelines found.[/dim]")
    except Exception as e:
        fmt.console.print(f"  [red]Error fetching pipelines: {e}[/red]")

    fmt.console.print()


def _name(field) -> str:
    if isinstance(field, dict):
        return field.get("displayName", "")
    return str(field) if field else ""


def _status(s) -> str:
    return {"inProgress": "[yellow]in progress[/yellow]", "completed": "completed",
             "notStarted": "[dim]not started[/dim]"}.get(str(s), str(s))


def _result(r) -> str:
    return {"succeeded": "[green]succeeded[/green]", "failed": "[red]failed[/red]",
            "canceled": "[dim]canceled[/dim]", "partiallySucceeded": "[yellow]partial[/yellow]"}.get(
        str(r), str(r) if r else "—")
