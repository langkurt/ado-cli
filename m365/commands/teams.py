"""Teams commands: list, find, channels, messages, send."""
import re

import click

from m365 import fmt
from m365.client import GraphClient


def _resolve_team(client: GraphClient, team_id_or_name: str) -> tuple[str, str]:
    """Return (id, name) — accepts full UUID or fuzzy display name."""
    data = client.get("/me/joinedTeams")
    teams = data.get("value", [])
    # Exact UUID match
    for t in teams:
        if t["id"] == team_id_or_name:
            return t["id"], t["displayName"]
    # Case-insensitive name match
    needle = team_id_or_name.lower()
    matches = [t for t in teams if needle in t["displayName"].lower()]
    if len(matches) == 1:
        return matches[0]["id"], matches[0]["displayName"]
    if len(matches) > 1:
        names = ", ".join(f'"{m["displayName"]}"' for m in matches)
        raise SystemExit(f"Ambiguous team name '{team_id_or_name}' matches: {names}")
    raise SystemExit(f"Team not found: '{team_id_or_name}'")


def _resolve_channel(client: GraphClient, team_id: str, channel_id_or_name: str) -> tuple[str, str]:
    """Return (id, name) — accepts full ID or fuzzy display name."""
    data = client.get(f"/teams/{team_id}/channels")
    channels = data.get("value", [])
    for c in channels:
        if c["id"] == channel_id_or_name:
            return c["id"], c["displayName"]
    needle = channel_id_or_name.lower()
    matches = [c for c in channels if needle in c["displayName"].lower()]
    if len(matches) == 1:
        return matches[0]["id"], matches[0]["displayName"]
    if len(matches) > 1:
        names = ", ".join(f'"{m["displayName"]}"' for m in matches)
        raise SystemExit(f"Ambiguous channel name '{channel_id_or_name}' matches: {names}")
    raise SystemExit(f"Channel not found: '{channel_id_or_name}'")


@click.group("teams")
def teams_group():
    """Microsoft Teams commands."""
    pass


@teams_group.command("list")
@click.pass_context
def teams_list(ctx):
    """List joined teams."""
    client: GraphClient = ctx.obj
    data = client.get("/me/joinedTeams")
    teams = data.get("value", [])

    if fmt.json_mode:
        fmt.output_json({"items": [{"id": t["id"], "name": t.get("displayName", ""), "description": t.get("description", "") or ""} for t in teams]})
        return

    rows = [(t.get("id", ""), t.get("displayName", ""), t.get("description", "") or "") for t in teams]
    fmt.table("Joined Teams", ["ID", "Name", "Description"], rows, ["dim"])


@teams_group.command("find")
@click.argument("name")
@click.pass_context
def teams_find(ctx, name):
    """Find a team by name and show its full ID."""
    client: GraphClient = ctx.obj
    team_id, team_name = _resolve_team(client, name)
    if fmt.json_mode:
        fmt.output_json({"id": team_id, "name": team_name})
    else:
        fmt.console.print(f"  Name: {team_name}")
        fmt.console.print(f"  ID:   {team_id}")


@teams_group.command("channels")
@click.argument("team")
@click.pass_context
def channels_list(ctx, team):
    """List channels in a team (name or ID)."""
    client: GraphClient = ctx.obj
    team_id, team_name = _resolve_team(client, team)
    data = client.get(f"/teams/{team_id}/channels")
    channels = data.get("value", [])

    rows = [(c.get("id", ""), c.get("displayName", ""), c.get("membershipType", "")) for c in channels]
    fmt.table(f"Channels · {team_name}", ["ID", "Name", "Type"], rows, ["dim"])


@teams_group.command("messages")
@click.argument("team")
@click.argument("channel")
@click.option("-n", "--count", default=20, help="Number of messages to show")
@click.pass_context
def channel_messages(ctx, team, channel, count):
    """Read messages from a channel (names or IDs)."""
    client: GraphClient = ctx.obj
    team_id, team_name = _resolve_team(client, team)
    channel_id, channel_name = _resolve_channel(client, team_id, channel)

    data = client.get(
        f"/teams/{team_id}/channels/{channel_id}/messages",
        params={"$top": count}
    )
    messages = data.get("value", [])

    if not messages:
        fmt.info("No messages in this channel.")
        return

    rows = []
    for m in reversed(messages):
        sender = (m.get("from") or {})
        name = (sender.get("user") or {}).get("displayName", "System")
        date = m.get("createdDateTime", "")[:16].replace("T", " ")
        body = re.sub(r"<[^>]+>", "", (m.get("body") or {}).get("content", "") or "").strip()[:70]
        if body:
            rows.append((date, name[:22], body))

    fmt.table(f"{team_name} · #{channel_name}", ["Time", "From", "Content"], rows)
