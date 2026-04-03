"""Auth commands: login, logout, status."""
import webbrowser

import click

from m365 import fmt
from m365.auth import token_store
from m365.auth.server import run_login_server


@click.group("auth")
def auth_group():
    """Authentication commands."""
    pass


@click.command()
@click.option("--port", default=9365, help="Local server port")
@click.option("--timeout", default=300, help="Seconds to wait for token")
def login(port, timeout):
    """Start local server and capture token from browser."""
    if not token_store.is_expired():
        info = token_store.summary()
        fmt.ok(f"Already logged in (expires {info['expires_at']}). Use --force or logout first.")
        return

    fmt.info(f"Starting login server on http://localhost:{port}")
    webbrowser.open(f"http://localhost:{port}")

    if run_login_server(port=port, timeout=timeout):
        info = token_store.summary()
        fmt.ok(f"Token captured! Expires: {info['expires_at']}")
    else:
        fmt.err("Timed out waiting for token. Make sure the userscript is installed and you have Teams/Outlook open.")


@click.command()
def logout():
    """Clear stored token."""
    token_store.clear()
    fmt.ok("Logged out — token cleared.")


@click.command()
def status():
    """Show current auth status."""
    info = token_store.summary()
    if info is None:
        fmt.err("Not logged in. Run: m365 login")
        raise SystemExit(1)

    expired = token_store.is_expired()
    if fmt.json_mode:
        fmt.output_json({**info, "expired": expired})
    else:
        state = "[red]EXPIRED[/red]" if expired else "[green]VALID[/green]"
        fmt.console.print(f"  Status:     {state}")
        fmt.console.print(f"  Expires:    {info['expires_at']}")
        fmt.console.print(f"  Scopes:     {info['scopes']}")
        fmt.console.print(f"  Captured:   {info['captured_at']}")


auth_group.add_command(login)
auth_group.add_command(logout)
auth_group.add_command(status)
