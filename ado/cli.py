"""Entry point: builds the CLI and wires up command groups."""
import sys

import click
from rich.traceback import install as install_rich_tb

from ado.client import ADOClient
from ado.commands.config_cmd import config_group
from ado.commands.pipelines import pipelines_group
from ado.commands.repos import repos_group
from ado.commands.wikis import wikis_group
from ado.commands.work_items import wi_group

install_rich_tb(show_locals=False)


@click.group()
@click.option("--org", envvar="ADO_ORG", default=None, help="Azure DevOps org (overrides config)")
@click.option("--project", "-p", envvar="ADO_PROJECT", default=None, help="Project name (overrides config)")
@click.pass_context
def cli(ctx: click.Context, org: str, project: str):
    """Azure DevOps CLI — repos, pipelines, work items, wikis."""
    ctx.ensure_object(dict)
    ctx.obj = ADOClient(org=org, project=project)


cli.add_command(config_group)
cli.add_command(repos_group)
cli.add_command(pipelines_group)
cli.add_command(wi_group)
cli.add_command(wikis_group)


if __name__ == "__main__":
    cli()
