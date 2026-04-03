"""Entry point: builds the CLI and wires up command groups."""
import sys

import click
import requests

from m365 import fmt
from m365.client import GraphClient
from m365.commands.auth_cmd import auth_group, login, logout, status
from m365.commands.profile import me_cmd
from m365.commands.teams import teams_group
from m365.commands.mail import mail_group
from m365.commands.calendar import calendar_group
from m365.commands.chats import chats_group
from m365.commands.todo import todo_group
from m365.commands.onedrive import drive_group


@click.group()
@click.option("--json", "as_json", is_flag=True, default=False, envvar="M365_JSON", help="Output as JSON")
@click.pass_context
def cli(ctx: click.Context, as_json: bool):
    """Microsoft 365 CLI — Teams, Mail, Calendar."""
    ctx.ensure_object(dict)
    fmt.json_mode = as_json
    ctx.obj = GraphClient()


# Top-level auth commands (m365 login, m365 logout, m365 status)
cli.add_command(login)
cli.add_command(logout)
cli.add_command(status)

# Feature groups
cli.add_command(me_cmd)
cli.add_command(teams_group)
cli.add_command(mail_group)
cli.add_command(calendar_group)
cli.add_command(chats_group)
cli.add_command(todo_group)
cli.add_command(drive_group)


def _main():
    try:
        cli(standalone_mode=False)
    except SystemExit as e:
        sys.exit(e.code)
    except click.exceptions.Abort:
        pass
    except click.exceptions.Exit as e:
        sys.exit(e.code)
    except requests.exceptions.ConnectionError:
        fmt.err("Connection error — check your network.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        fmt.err(f"HTTP error: {e}")
        sys.exit(1)
    except Exception as e:
        fmt.err(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    _main()
