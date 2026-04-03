"""Mail commands: list, show."""
import click

from m365 import fmt
from m365.client import GraphClient


@click.group("mail")
def mail_group():
    """Outlook mail commands."""
    pass


@mail_group.command("list")
@click.option("-n", "--count", default=10, help="Number of messages to show")
@click.pass_context
def mail_list(ctx, count):
    """List recent emails."""
    client: GraphClient = ctx.obj
    data = client.get("/me/messages", params={"$top": count, "$orderby": "receivedDateTime desc"})
    messages = data.get("value", [])

    rows = []
    for m in messages:
        sender = m.get("from", {}).get("emailAddress", {}).get("name", "Unknown")
        subject = m.get("subject", "(no subject)")
        date = m.get("receivedDateTime", "")[:10]
        read = "" if m.get("isRead") else "●"
        rows.append((read, date, sender[:30], subject[:60]))

    fmt.table("Inbox", ["", "Date", "From", "Subject"], rows)
