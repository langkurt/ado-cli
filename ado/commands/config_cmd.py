"""ado config — manage org/project defaults."""
import click

from ado import config, fmt


@click.group("config")
def config_group():
    """Manage ado-cli configuration."""


@config_group.command("set")
@click.option("--org", default=None, help="Azure DevOps organization name")
@click.option("--project", default=None, help="Default project name")
def config_set(org: str, project: str):
    """Set default org and/or project."""
    if org:
        config.set_value("org", org)
        fmt.ok(f"org = {org}")
    if project:
        config.set_value("project", project)
        fmt.ok(f"project = {project}")
    if not org and not project:
        fmt.err("Provide --org and/or --project.")


@config_group.command("show")
def config_show():
    """Show current configuration."""
    from ado.config import CONFIG_PATH
    fmt.console.print(f"[dim]Config file:[/dim] {CONFIG_PATH}")
    for key in ("org", "project", "pat"):
        val = config.get(key)
        display = (val[:4] + "…" + val[-4:]) if key == "pat" and val else (val or "[dim]not set[/dim]")
        fmt.console.print(f"  {key:12s} {display}")
