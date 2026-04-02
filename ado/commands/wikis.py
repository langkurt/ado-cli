"""ado wikis — wiki commands."""
import click

from ado import fmt
from ado.client import ADOClient


@click.group("wikis")
def wikis_group():
    """Wiki pages."""


@wikis_group.command("list")
@click.pass_obj
def wikis_list(client: ADOClient):
    """List wikis in the project."""
    wikis = client.wiki.get_all_wikis(project=client.project)
    fmt.table(
        f"Wikis · {client.project}",
        ["ID", "Name", "Type", "Mapped Path"],
        [
            [w.id, w.name, w.type, getattr(w, "mapped_path", "")]
            for w in wikis
        ],
        col_styles=["cyan", "bold", "dim", None],
    )


@wikis_group.command("page")
@click.argument("path")
@click.option("--wiki", "-w", required=True, help="Wiki ID or name")
@click.pass_obj
def wikis_page(client: ADOClient, path: str, wiki: str):
    """Get a wiki page by path."""
    page = client.wiki.get_page(
        project=client.project,
        wiki_identifier=wiki,
        path=path,
        include_content=True,
    )
    if page and page.page:
        fmt.console.print(f"\n[bold]{path}[/bold]\n")
        fmt.console.print(page.page.content or "[dim](empty)[/dim]")
    else:
        fmt.err(f"Page not found: {path}")


@wikis_group.command("pages")
@click.option("--wiki", "-w", required=True, help="Wiki ID or name")
@click.option("--path", default="/", show_default=True, help="Root path to list from")
@click.option("--depth", default=2, show_default=True, type=int)
@click.pass_obj
def wikis_pages(client: ADOClient, wiki: str, path: str, depth: int):
    """List pages in a wiki."""
    page = client.wiki.get_page(
        project=client.project,
        wiki_identifier=wiki,
        path=path,
        recursion_level=depth,
    )
    if not page or not page.page:
        fmt.err("No pages found.")
        return

    def _print_tree(p, indent=0):
        label = ("  " * indent) + (p.path or "/")
        fmt.console.print(label)
        for sub in (p.sub_pages or []):
            _print_tree(sub, indent + 1)

    _print_tree(page.page)
