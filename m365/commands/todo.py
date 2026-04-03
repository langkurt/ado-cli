"""Microsoft To Do commands: lists, tasks, create, complete."""
import click

from m365 import fmt
from m365.client import GraphClient


@click.group("todo")
def todo_group():
    """Microsoft To Do commands."""
    pass


@todo_group.command("lists")
@click.pass_context
def todo_lists(ctx):
    """List all task lists."""
    client: GraphClient = ctx.obj
    data = client.get("/me/todo/lists")
    lists = data.get("value", [])

    if not lists:
        fmt.info("No task lists found.")
        return

    rows = [(l.get("id", "")[:12], l.get("displayName", ""), "✓" if l.get("isOwner") else "") for l in lists]
    fmt.table("Task Lists", ["ID", "Name", "Owner"], rows, ["dim"])


@todo_group.command("tasks")
@click.argument("list_id")
@click.option("--all", "show_all", is_flag=True, help="Include completed tasks")
@click.pass_context
def todo_tasks(ctx, list_id, show_all):
    """List tasks in a task list."""
    client: GraphClient = ctx.obj
    params = {"$orderby": "createdDateTime desc", "$top": 50}
    if not show_all:
        params["$filter"] = "status ne 'completed'"
    data = client.get(f"/me/todo/lists/{list_id}/tasks", params=params)
    tasks = data.get("value", [])

    if not tasks:
        fmt.info("No tasks found.")
        return

    rows = []
    for t in tasks:
        status = "✓" if t.get("status") == "completed" else "○"
        title = t.get("title", "")[:50]
        due = ""
        if dd := t.get("dueDateTime"):
            due = dd.get("dateTime", "")[:10]
        importance = t.get("importance", "")
        tid = t.get("id", "")[:12]
        rows.append((status, tid, title, due, importance))

    fmt.table("Tasks", ["", "ID", "Title", "Due", "Priority"], rows)


@todo_group.command("add")
@click.argument("list_id")
@click.option("-t", "--title", required=True, help="Task title")
@click.option("--due", default=None, help="Due date (YYYY-MM-DD)")
@click.pass_context
def todo_add(ctx, list_id, title, due):
    """Create a new task."""
    client: GraphClient = ctx.obj
    body = {"title": title}
    if due:
        body["dueDateTime"] = {"dateTime": f"{due}T00:00:00", "timeZone": "UTC"}
    data = client.post(f"/me/todo/lists/{list_id}/tasks", json=body)
    fmt.ok(f"Task created: {data.get('title', title)}")


@todo_group.command("complete")
@click.argument("list_id")
@click.argument("task_id")
@click.pass_context
def todo_complete(ctx, list_id, task_id):
    """Mark a task as completed."""
    client: GraphClient = ctx.obj
    client.patch(f"/me/todo/lists/{list_id}/tasks/{task_id}", json={
        "status": "completed"
    })
    fmt.ok("Task marked as completed.")
