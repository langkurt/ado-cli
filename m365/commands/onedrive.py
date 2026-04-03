"""OneDrive commands: ls, download, upload, search."""
import os

import click

from m365 import fmt
from m365.client import GraphClient


@click.group("drive")
def drive_group():
    """OneDrive file commands."""
    pass


@drive_group.command("ls")
@click.argument("path", default="/")
@click.pass_context
def drive_ls(ctx, path):
    """List files and folders."""
    client: GraphClient = ctx.obj
    if path == "/":
        data = client.get("/me/drive/root/children", params={"$top": 50})
    else:
        clean = path.strip("/")
        data = client.get(f"/me/drive/root:/{clean}:/children", params={"$top": 50})
    items = data.get("value", [])

    if not items:
        fmt.info("Empty folder.")
        return

    rows = []
    for item in items:
        name = item.get("name", "")
        is_folder = "folder" in item
        icon = "📁" if is_folder else "📄"
        size = ""
        if not is_folder:
            b = item.get("size", 0)
            if b < 1024:
                size = f"{b} B"
            elif b < 1024 * 1024:
                size = f"{b / 1024:.1f} KB"
            else:
                size = f"{b / (1024 * 1024):.1f} MB"
        modified = item.get("lastModifiedDateTime", "")[:16].replace("T", " ")
        rows.append((icon, name, size, modified))

    fmt.table(f"OneDrive: {path}", ["", "Name", "Size", "Modified"], rows)


@drive_group.command("download")
@click.argument("remote_path")
@click.option("-o", "--output", default=None, help="Local output path (defaults to filename)")
@click.pass_context
def drive_download(ctx, remote_path, output):
    """Download a file from OneDrive."""
    client: GraphClient = ctx.obj
    clean = remote_path.strip("/")

    # Get download URL
    meta = client.get(f"/me/drive/root:/{clean}")
    download_url = meta.get("@microsoft.graph.downloadUrl")
    if not download_url:
        fmt.err("Could not get download URL. Is this a file?")
        raise SystemExit(1)

    filename = output or meta.get("name", os.path.basename(clean))

    import requests
    resp = requests.get(download_url, stream=True)
    resp.raise_for_status()
    with open(filename, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    size = os.path.getsize(filename)
    fmt.ok(f"Downloaded: {filename} ({size:,} bytes)")


@drive_group.command("upload")
@click.argument("local_path")
@click.option("-d", "--dest", default=None, help="Remote folder path (defaults to root)")
@click.pass_context
def drive_upload(ctx, local_path, dest):
    """Upload a file to OneDrive."""
    client: GraphClient = ctx.obj

    if not os.path.isfile(local_path):
        fmt.err(f"File not found: {local_path}")
        raise SystemExit(1)

    filename = os.path.basename(local_path)
    if dest:
        remote = f"/me/drive/root:/{dest.strip('/')}/{filename}:/content"
    else:
        remote = f"/me/drive/root:/{filename}:/content"

    with open(local_path, "rb") as f:
        content = f.read()

    client.put(remote, data=content)
    fmt.ok(f"Uploaded: {filename} → OneDrive:{dest or '/'}")


@drive_group.command("search")
@click.argument("query")
@click.pass_context
def drive_search(ctx, query):
    """Search for files in OneDrive."""
    client: GraphClient = ctx.obj
    data = client.get(f"/me/drive/root/search(q='{query}')", params={"$top": 20})
    items = data.get("value", [])

    if not items:
        fmt.info("No files found.")
        return

    rows = []
    for item in items:
        name = item.get("name", "")
        path = item.get("parentReference", {}).get("path", "").replace("/drive/root:", "") or "/"
        modified = item.get("lastModifiedDateTime", "")[:16].replace("T", " ")
        rows.append((name[:40], path[:40], modified))

    fmt.table(f"Search: {query}", ["Name", "Path", "Modified"], rows)
