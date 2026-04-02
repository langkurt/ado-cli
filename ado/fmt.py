"""Rich-based output helpers."""
from rich.console import Console
from rich.table import Table

console = Console()


def table(title: str, columns: list, rows: list, col_styles: list = None) -> None:
    t = Table(title=title, show_lines=False)
    styles = col_styles or []
    for i, col in enumerate(columns):
        style = styles[i] if i < len(styles) else None
        t.add_column(col, style=style, no_wrap=(i == 0))
    for row in rows:
        t.add_row(*[str(c) if c is not None else "" for c in row])
    console.print(t)


def ok(msg: str) -> None:
    console.print(f"[green]✓[/green] {msg}")


def err(msg: str) -> None:
    console.print(f"[red]✗[/red] {msg}")


def info(msg: str) -> None:
    console.print(f"[cyan]ℹ[/cyan] {msg}")
