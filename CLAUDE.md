# ado-cli

Azure DevOps CLI for use with Claude Code.

## Setup

```bash
# Activate venv
source .venv/bin/activate

# Set org and project (saved to ~/.ado-cli/config.yaml)
ado config set --org <your-org> --project <your-project>

# Or use env vars (ADO_PAT already in .env)
export ADO_ORG=myorg
export ADO_PROJECT=myproject
```

PAT is read from `ADO_PAT` in `.env` (already present).

## Commands

```
ado config show/set          # view or set org/project defaults

ado repos list               # list repos
ado repos pr list [-r repo] [-s status]
ado repos pr show <id> -r <repo>
ado repos pr create -r <repo> --title "…" --source <branch> [--target main]

ado pipelines list
ado pipelines runs <pipeline-id> [-n 20]
ado pipelines run  <pipeline-id> [-b branch] [-v KEY=VALUE]
ado pipelines show <run-id>

ado wi list [-t "Bug"] [-a me] [-s Active] [-n 25]
ado wi show <id>
ado wi create -t "Task" --title "…" [-d description] [-a "Name"]
ado wi update <id> [--title …] [--state Active] [--assigned-to …]

ado wikis list
ado wikis pages  --wiki <id>  [--path /] [--depth 2]
ado wikis page   <path>       --wiki <id>
```

Global flags: `--org <org>` and `-p <project>` override config for any command.

## Development

```bash
source .venv/bin/activate
pip install -e .
```
