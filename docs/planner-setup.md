# Planner Setup

A planner is a GitHub Codespace that runs Claude Code for remote plan execution.

## Quick Start

### 1. Create a Planner

```bash
erk planner create --run
```

This creates a GitHub Codespace and automatically registers it. The repo must have a `.devcontainer/devcontainer.json` (see below).

Without `--run`, it prints the `gh` command for review.

### 2. Configure Authentication

```bash
erk planner configure erk-planner-node
```

This opens an SSH session with a setup checklist:

1. **GitHub CLI**: `gh auth login`
2. **Claude Code**: Run `claude` and authenticate

Exit the session when done and confirm configuration.

### 3. Connect

```bash
erk planner connect
```

This SSHs into the codespace and launches Claude.

## Commands

| Command                          | Description                              |
| -------------------------------- | ---------------------------------------- |
| `erk planner create [name]`      | Create codespace and register as planner |
| `erk planner configure <name>`   | Configure authentication (gh, claude)    |
| `erk planner connect [name]`     | Connect to planner and launch Claude     |
| `erk planner list`               | Show registered planners                 |
| `erk planner set-default <name>` | Set the default planner                  |
| `erk planner register <name>`    | Register an existing codespace           |
| `erk planner unregister <name>`  | Remove a registered planner              |

## Devcontainer

For repos that will be used as planners, add this `.devcontainer/devcontainer.json`:

```json
{
  "name": "erk-planning",
  "image": "mcr.microsoft.com/devcontainers/python:3.13",
  "features": {
    "ghcr.io/devcontainers/features/github-cli:1": {},
    "ghcr.io/devcontainers/features/sshd:1": {
      "version": "latest"
    }
  },
  "postCreateCommand": "curl -fsSL https://claude.ai/install.sh | bash && pip install uv && uv sync"
}
```

This pre-installs GitHub CLI, Claude Code, and uv so the codespace is ready for planning work.
