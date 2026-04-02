"""Output helpers — rich tables for humans, JSON for agents (--json flag)."""
import json as _json
import sys

from rich.console import Console
from rich.table import Table

console = Console()

# Set to True when --json is passed; commands check this to switch output mode.
json_mode: bool = False


def table(title: str, columns: list, rows: list, col_styles: list = None) -> None:
    if json_mode:
        data = [dict(zip(columns, row)) for row in rows]
        _print_json({"title": title, "items": data})
        return
    t = Table(title=title, show_lines=False)
    styles = col_styles or []
    for i, col in enumerate(columns):
        style = styles[i] if i < len(styles) else None
        t.add_column(col, style=style, no_wrap=(i == 0))
    for row in rows:
        t.add_row(*[str(c) if c is not None else "" for c in row])
    console.print(t)


def output_json(data) -> None:
    """Emit structured JSON directly (used by commands that build their own dicts)."""
    _print_json(data)


def ok(msg: str) -> None:
    if json_mode:
        _print_json({"status": "ok", "message": msg})
    else:
        console.print(f"[green]✓[/green] {msg}")


def err(msg: str) -> None:
    if json_mode:
        _print_json({"status": "error", "message": msg}, file=sys.stderr)
    else:
        console.print(f"[red]✗[/red] {msg}")


def info(msg: str) -> None:
    if json_mode:
        _print_json({"status": "info", "message": msg})
    else:
        console.print(f"[cyan]ℹ[/cyan] {msg}")


def _print_json(data, file=sys.stdout) -> None:
    print(_json.dumps(data, default=str, indent=2), file=file)
