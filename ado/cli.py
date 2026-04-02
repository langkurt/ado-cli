"""Entry point: builds the CLI and wires up command groups."""
import sys
import warnings

# Must suppress before any imports that load urllib3 transitively
warnings.filterwarnings("ignore", message=".*NotOpenSSL.*")
try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except ImportError:
    pass

import click
from azure.devops.exceptions import AzureDevOpsAuthenticationError, AzureDevOpsServiceError

from ado import fmt
from ado.client import ADOClient
from ado.commands.config_cmd import config_group
from ado.commands.pipelines import pipelines_group
from ado.commands.repos import repos_group
from ado.commands.wikis import wikis_group
from ado.commands.work_items import wi_group


@click.group()
@click.option("--org", envvar="ADO_ORG", default=None, help="Azure DevOps org (overrides config)")
@click.option("--project", "-p", envvar="ADO_PROJECT", default=None, help="Project name (overrides config)")
@click.option("--json", "as_json", is_flag=True, default=False, envvar="ADO_JSON", help="Output as JSON (for agent/script use)")
@click.pass_context
def cli(ctx: click.Context, org: str, project: str, as_json: bool):
    """Azure DevOps CLI — repos, pipelines, work items, wikis."""
    ctx.ensure_object(dict)
    fmt.json_mode = as_json
    ctx.obj = ADOClient(org=org, project=project)


def _main():
    try:
        cli(standalone_mode=False)
    except AzureDevOpsAuthenticationError:
        fmt.err("Authentication failed. Check your ADO_PAT and ensure it has the required scopes.")
        sys.exit(1)
    except AzureDevOpsServiceError as e:
        fmt.err(f"ADO error: {e}")
        sys.exit(1)
    except SystemExit as e:
        sys.exit(e.code)
    except click.exceptions.Abort:
        pass
    except click.exceptions.Exit as e:
        sys.exit(e.code)
    except Exception as e:
        fmt.err(f"Unexpected error: {e}")
        sys.exit(1)


cli.add_command(config_group)
cli.add_command(repos_group)
cli.add_command(pipelines_group)
cli.add_command(wi_group)
cli.add_command(wikis_group)


if __name__ == "__main__":
    _main()
