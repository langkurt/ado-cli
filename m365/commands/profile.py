"""Profile command: m365 me."""
import click

from m365 import fmt
from m365.client import GraphClient


@click.command("me")
@click.pass_context
def me_cmd(ctx):
    """Show current user profile (GET /me)."""
    client: GraphClient = ctx.obj
    data = client.get("/me")

    if fmt.json_mode:
        fmt.output_json(data)
    else:
        fmt.console.print(f"  Name:    {data.get('displayName') or 'N/A'}")
        fmt.console.print(f"  Email:   {data.get('mail') or data.get('userPrincipalName') or 'N/A'}")
        fmt.console.print(f"  Title:   {data.get('jobTitle') or 'N/A'}")
        fmt.console.print(f"  ID:      {data.get('id') or 'N/A'}")
