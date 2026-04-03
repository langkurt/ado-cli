"""Chat commands: list chats, read messages, send message — uses Teams internal API."""
import re
from urllib.parse import quote

import click

from m365 import fmt
from m365.client import TeamsClient


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").replace("&nbsp;", " ").strip()


@click.group("chats")
def chats_group():
    """Teams chat commands."""
    pass


@chats_group.command("list")
@click.option("-n", "--count", default=50, help="Number of chats to fetch")
@click.option("--search", default=None, help="Filter by participant name, topic, or message content")
@click.pass_context
def chats_list(ctx, count, search):
    """List recent chats."""
    client = TeamsClient()
    data = client.get("/users/ME/conversations", params={
        "pageSize": count,
        "view": "msnp24Equivalent",  # includes member roster
    })
    chats = data.get("conversations", [])

    rows = []
    for c in chats:
        tp = c.get("threadProperties", {})
        thread_type = tp.get("threadType", "")
        if thread_type not in ("chat", ""):
            continue
        cid = c.get("id", "")
        topic = tp.get("topic", "")
        last = c.get("lastMessage") or {}
        from_name = last.get("imdisplayname", "") or ""
        preview = _strip_html(last.get("content", ""))[:45]
        time = (last.get("originalarrivaltime") or last.get("composetime") or "")[:10]

        # Build member list from roster
        members_raw = tp.get("members", "")
        member_names = []
        if members_raw:
            # members is a JSON string of member objects
            try:
                import json as _json
                member_list = _json.loads(members_raw) if isinstance(members_raw, str) else members_raw
                member_names = [m.get("displayName", "") for m in member_list if m.get("displayName")]
            except Exception:
                pass
        members_str = ", ".join(member_names)

        display = topic or members_str or from_name or cid[:20]
        searchable = (display + preview + cid + members_str + from_name).lower()
        if search and search.lower() not in searchable:
            continue
        rows.append((cid[:45], display[:35], time, preview))

    if not rows:
        fmt.info("No chats found.")
        return

    fmt.table("Chats", ["ID", "Topic / Participants", "Date", "Preview"], rows, ["dim"])


@chats_group.command("messages")
@click.argument("chat_id")
@click.option("-n", "--count", default=20, help="Number of messages to show")
@click.pass_context
def chats_messages(ctx, chat_id, count):
    """Read messages from a chat."""
    client = TeamsClient()
    encoded = quote(chat_id, safe="")
    data = client.get(f"/users/ME/conversations/{encoded}/messages", params={"pageSize": count})
    messages = data.get("messages", [])

    if not messages:
        fmt.info("No messages.")
        return

    rows = []
    for m in reversed(messages):
        if m.get("messagetype", "") not in ("RichText/Html", "Text", ""):
            continue
        name = (m.get("imdisplayname") or "System")[:22]
        time = (m.get("originalarrivaltime") or m.get("composetime") or "")[:16].replace("T", " ")
        body = _strip_html(m.get("content", ""))[:70]
        rows.append((time, name, body))

    fmt.table("Messages", ["Time", "From", "Content"], rows)


@chats_group.command("send")
@click.argument("chat_id")
@click.option("-m", "--message", required=True, help="Message text")
@click.pass_context
def chats_send(ctx, chat_id, message):
    """Send a message to a chat."""
    client = TeamsClient()
    encoded = quote(chat_id, safe="")
    client.post(f"/users/ME/conversations/{encoded}/messages", json={
        "content": f"<p>{message}</p>",
        "messagetype": "RichText/Html",
        "contenttype": "text",
    })
    fmt.ok("Message sent.")
