"""ado repos — repository and pull request commands."""
import click
from azure.devops.exceptions import AzureDevOpsServiceError
from azure.devops.v7_1.git.models import (
    GitPullRequest,
    GitPullRequestSearchCriteria,
    ResourceRef,
)

from ado import fmt
from ado.client import ADOClient


@click.group("repos")
def repos_group():
    """Git repositories and pull requests."""


@repos_group.command("list")
@click.pass_obj
def repos_list(client: ADOClient):
    """List repositories in the project."""
    repos = client.git.get_repositories(project=client.project)
    fmt.table(
        f"Repos · {client.project}",
        ["ID", "Name", "Default Branch", "Remote URL"],
        [
            [
                r.id[:8],
                r.name,
                (r.default_branch or "").replace("refs/heads/", ""),
                r.remote_url,
            ]
            for r in repos
        ],
        col_styles=["dim", "bold", None, "blue"],
    )


# ── Pull requests ──────────────────────────────────────────────────────────────

@repos_group.group("pr")
def pr_group():
    """Pull request operations."""


@pr_group.command("list")
@click.option("--repo", "-r", default=None, help="Repository name (default: all repos)")
@click.option(
    "--status",
    "-s",
    default="active",
    type=click.Choice(["active", "completed", "abandoned", "all"]),
)
@click.option("--author", "-a", default=None, help="Filter by author display name (or 'me')")
@click.pass_obj
def pr_list(client: ADOClient, repo: str, status: str, author: str):
    """List pull requests across all repos or a specific repo."""
    search = GitPullRequestSearchCriteria(status=status)
    if repo:
        prs = client.git.get_pull_requests(repo, search, project=client.project)
        repos = [repo]
    else:
        all_repos = client.git.get_repositories(project=client.project)
        prs = []
        repos = []
        for r in all_repos:
            try:
                batch = client.git.get_pull_requests(r.id, search, project=client.project)
                prs.extend(batch)
                repos.extend([r.name] * len(batch))
            except AzureDevOpsServiceError:
                pass

    # Author filter (post-fetch since ADO API doesn't support it natively)
    if author and prs:
        me_names = None
        if author.lower() == "me":
            try:
                me_names = client.core.get_team_members  # fallback: match by display name substring
            except Exception:
                pass
        needle = author.lower()
        filtered_prs, filtered_repos = [], []
        for pr, repo_name in zip(prs, repos):
            creator = pr.created_by.display_name.lower() if pr.created_by else ""
            if needle == "me":
                import os
                me_upn = os.getenv("ADO_USER", "").lower()
                match = me_upn and me_upn.split("@")[0] in creator
            else:
                match = needle in creator
            if match:
                filtered_prs.append(pr)
                filtered_repos.append(repo_name)
        prs, repos = filtered_prs, filtered_repos

    if not prs:
        fmt.info("No pull requests found.")
        return

    fmt.table(
        f"PRs [{status}]",
        ["ID", "Repo", "Title", "Author", "Source → Target"],
        [
            [
                pr.pull_request_id,
                repos[i] if not repo else repo,
                pr.title[:60],
                pr.created_by.display_name,
                f"{pr.source_ref_name.replace('refs/heads/', '')} → {pr.target_ref_name.replace('refs/heads/', '')}",
            ]
            for i, pr in enumerate(prs)
        ],
        col_styles=["cyan", "dim", "bold", None, "yellow"],
    )


@pr_group.command("show")
@click.argument("pr_id", type=int)
@click.option("--repo", "-r", required=True, help="Repository name")
@click.pass_obj
def pr_show(client: ADOClient, pr_id: int, repo: str):
    """Show pull request details."""
    pr: GitPullRequest = client.git.get_pull_request(repo, pr_id, project=client.project)
    reviewers = pr.reviewers or []
    if fmt.json_mode:
        fmt.output_json({
            "id": pr.pull_request_id,
            "title": pr.title,
            "status": pr.status,
            "author": pr.created_by.display_name,
            "source_branch": pr.source_ref_name.replace("refs/heads/", ""),
            "target_branch": pr.target_ref_name.replace("refs/heads/", ""),
            "description": pr.description or "",
            "reviewers": [{"name": r.display_name, "vote": r.vote} for r in reviewers],
        })
        return
    c = fmt.console
    c.print(f"\n[bold]PR #{pr.pull_request_id}[/bold] · {pr.title}")
    c.print(f"[dim]Status:[/dim] {pr.status}")
    c.print(f"[dim]Author:[/dim] {pr.created_by.display_name}")
    c.print(
        f"[dim]Branch:[/dim] {pr.source_ref_name.replace('refs/heads/', '')} "
        f"→ {pr.target_ref_name.replace('refs/heads/', '')}"
    )
    if pr.description:
        c.print(f"\n{pr.description}\n")
    if reviewers:
        fmt.table(
            "Reviewers",
            ["Name", "Vote"],
            [[r.display_name, _vote_label(r.vote)] for r in reviewers],
        )


@pr_group.command("create")
@click.option("--repo", "-r", required=True)
@click.option("--title", "-t", required=True)
@click.option("--source", required=True, help="Source branch name")
@click.option("--target", default="main", show_default=True, help="Target branch name")
@click.option("--description", "-d", default="")
@click.option("--draft", is_flag=True, default=False)
@click.pass_obj
def pr_create(client: ADOClient, repo: str, title: str, source: str, target: str, description: str, draft: bool):
    """Create a pull request."""
    pr = client.git.create_pull_request(
        GitPullRequest(
            title=title,
            description=description,
            source_ref_name=f"refs/heads/{source}",
            target_ref_name=f"refs/heads/{target}",
            is_draft=draft,
        ),
        repo,
        project=client.project,
    )
    fmt.ok(f"Created PR #{pr.pull_request_id}: {pr.title}")
    fmt.console.print(f"[blue]https://dev.azure.com/{client.org}/{client.project}/_git/{repo}/pullrequest/{pr.pull_request_id}[/blue]")


def _vote_label(vote: int) -> str:
    return {10: "[green]Approved[/green]", 5: "[yellow]Approved w/ suggestions[/yellow]",
            0: "No vote", -5: "[red]Waiting[/red]", -10: "[red]Rejected[/red]"}.get(vote, str(vote))
