"""Calendar commands: list events, today, week view."""
from datetime import datetime, timedelta, timezone

import click

from m365 import fmt
from m365.client import GraphClient


@click.group("calendar")
def calendar_group():
    """Outlook calendar commands."""
    pass


@calendar_group.command("list")
@click.option("--days", default=7, help="Number of days ahead to show")
@click.pass_context
def calendar_list(ctx, days):
    """List upcoming events."""
    client: GraphClient = ctx.obj
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)

    data = client.get("/me/calendarView", params={
        "startDateTime": now.isoformat(),
        "endDateTime": end.isoformat(),
        "$orderby": "start/dateTime",
        "$top": 50,
    })
    events = data.get("value", [])

    if not events:
        fmt.info(f"No events in the next {days} days.")
        return

    rows = []
    for e in events:
        start = e.get("start", {}).get("dateTime", "")[:16].replace("T", " ")
        end_t = e.get("end", {}).get("dateTime", "")[:16].replace("T", " ")
        subject = e.get("subject", "(no subject)")
        organizer = e.get("organizer", {}).get("emailAddress", {}).get("name", "")
        location = e.get("location", {}).get("displayName", "")
        status = e.get("showAs", "")
        rows.append((start, end_t, subject[:50], organizer[:25], location[:20], status))

    fmt.table("Upcoming Events", ["Start", "End", "Subject", "Organizer", "Location", "Status"], rows)


@calendar_group.command("today")
@click.pass_context
def calendar_today(ctx):
    """Show today's events."""
    client: GraphClient = ctx.obj
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    data = client.get("/me/calendarView", params={
        "startDateTime": start.isoformat(),
        "endDateTime": end.isoformat(),
        "$orderby": "start/dateTime",
        "$top": 50,
    })
    events = data.get("value", [])

    if not events:
        fmt.info("No events today.")
        return

    rows = []
    for e in events:
        start_t = e.get("start", {}).get("dateTime", "")[:16].replace("T", " ")
        end_t = e.get("end", {}).get("dateTime", "")[:16].replace("T", " ")
        subject = e.get("subject", "(no subject)")
        location = e.get("location", {}).get("displayName", "")
        status = e.get("showAs", "")
        rows.append((start_t[11:], end_t[11:], subject[:55], location[:25], status))

    fmt.table("Today's Events", ["Start", "End", "Subject", "Location", "Status"], rows)
