"""ado wi — work item commands."""
import click
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation, Wiql

from ado import fmt
from ado.client import ADOClient


@click.group("wi")
def wi_group():
    """Work items (bugs, tasks, stories, etc.)."""


@wi_group.command("list")
@click.option("--type", "-t", "wi_type", default=None, help="Work item type (Bug, Task, User Story…)")
@click.option("--assigned-to", "-a", default=None, help="Assigned to (display name or 'me')")
@click.option("--state", "-s", default=None, help="State filter (Active, Resolved, Closed…)")
@click.option("--limit", "-n", default=25, show_default=True)
@click.pass_obj
def wi_list(client: ADOClient, wi_type: str, assigned_to: str, state: str, limit: int):
    """List work items via WIQL query."""
    where_parts = [f"[System.TeamProject] = '{client.project}'"]
    if wi_type:
        where_parts.append(f"[System.WorkItemType] = '{wi_type}'")
    if assigned_to:
        name = "@Me" if assigned_to.lower() == "me" else f"'{assigned_to}'"
        where_parts.append(f"[System.AssignedTo] = {name}")
    if state:
        where_parts.append(f"[System.State] = '{state}'")

    query = (
        "SELECT [System.Id], [System.Title], [System.WorkItemType], "
        "[System.State], [System.AssignedTo] "
        f"FROM WorkItems WHERE {' AND '.join(where_parts)} "
        "ORDER BY [System.ChangedDate] DESC"
    )
    result = client.work_item_tracking.query_by_wiql(Wiql(query=query))
    refs = (result.work_items or [])[:limit]

    if not refs:
        fmt.info("No work items found.")
        return

    ids = [r.id for r in refs]
    items = client.work_item_tracking.get_work_items(ids=ids, error_policy="omit")

    fmt.table(
        f"Work Items · {client.project}",
        ["ID", "Type", "State", "Assigned To", "Title"],
        [
            [
                wi.id,
                wi.fields.get("System.WorkItemType", ""),
                wi.fields.get("System.State", ""),
                _name(wi.fields.get("System.AssignedTo")),
                wi.fields.get("System.Title", "")[:70],
            ]
            for wi in items
        ],
        col_styles=["cyan", "dim", "yellow", "dim", "bold"],
    )


@wi_group.command("show")
@click.argument("wi_id", type=int)
@click.pass_obj
def wi_show(client: ADOClient, wi_id: int):
    """Show a work item."""
    wi = client.work_item_tracking.get_work_item(wi_id)
    f = wi.fields
    c = fmt.console
    c.print(f"\n[bold]#{wi.id}[/bold] {f.get('System.Title')}")
    c.print(f"[dim]Type:[/dim]        {f.get('System.WorkItemType')}")
    c.print(f"[dim]State:[/dim]       {f.get('System.State')}")
    c.print(f"[dim]Assigned To:[/dim] {_name(f.get('System.AssignedTo'))}")
    c.print(f"[dim]Area:[/dim]        {f.get('System.AreaPath')}")
    c.print(f"[dim]Iteration:[/dim]   {f.get('System.IterationPath')}")
    desc = f.get("System.Description") or ""
    if desc:
        # strip simple HTML tags for terminal
        import re
        desc = re.sub(r"<[^>]+>", "", desc).strip()
        c.print(f"\n{desc[:500]}\n")


@wi_group.command("create")
@click.option("--type", "-t", "wi_type", required=True, help="Work item type (Bug, Task, User Story…)")
@click.option("--title", required=True)
@click.option("--description", "-d", default="")
@click.option("--assigned-to", "-a", default=None)
@click.option("--area", default=None)
@click.option("--iteration", default=None)
@click.pass_obj
def wi_create(client: ADOClient, wi_type: str, title: str, description: str, assigned_to: str, area: str, iteration: str):
    """Create a work item."""
    ops = [
        _patch("/fields/System.Title", title),
    ]
    if description:
        ops.append(_patch("/fields/System.Description", description))
    if assigned_to:
        ops.append(_patch("/fields/System.AssignedTo", assigned_to))
    if area:
        ops.append(_patch("/fields/System.AreaPath", area))
    if iteration:
        ops.append(_patch("/fields/System.IterationPath", iteration))

    wi = client.work_item_tracking.create_work_item(
        document=ops,
        project=client.project,
        type=wi_type,
    )
    fmt.ok(f"Created #{wi.id}: {wi.fields.get('System.Title')}")


@wi_group.command("update")
@click.argument("wi_id", type=int)
@click.option("--title", default=None)
@click.option("--state", "-s", default=None)
@click.option("--assigned-to", "-a", default=None)
@click.pass_obj
def wi_update(client: ADOClient, wi_id: int, title: str, state: str, assigned_to: str):
    """Update a work item field."""
    ops = []
    if title:
        ops.append(_patch("/fields/System.Title", title))
    if state:
        ops.append(_patch("/fields/System.State", state))
    if assigned_to:
        ops.append(_patch("/fields/System.AssignedTo", assigned_to))
    if not ops:
        fmt.err("No fields to update.")
        return
    wi = client.work_item_tracking.update_work_item(document=ops, id=wi_id)
    fmt.ok(f"Updated #{wi.id}")


def _patch(path: str, value) -> JsonPatchOperation:
    return JsonPatchOperation(op="add", path=path, value=value)


def _name(field) -> str:
    if isinstance(field, dict):
        return field.get("displayName", "")
    return str(field) if field else ""
