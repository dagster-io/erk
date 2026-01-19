# Advanced Configuration

Optional capabilities, init flags, and troubleshooting for erk initialization.

**Prerequisites:** Complete [Installation](installation.md) first.

## Capabilities

Capabilities are optional features you can enable. View all available capabilities:

```bash
erk init capability list
```

**Project capabilities** (committed to repo, shared by team):

| Capability                  | Description                                         |
| --------------------------- | --------------------------------------------------- |
| `devrun-agent`              | Safe execution agent for pytest/ty/ruff/make/gt     |
| `devrun-reminder`           | Remind agent to use devrun for CI tool commands     |
| `dignified-python`          | Python coding standards (LBYL, modern types, ABCs)  |
| `dignified-python-reminder` | Remind agent to follow dignified-python standards   |
| `dignified-review`          | Python code review (via convention-based system)    |
| `erk-bash-permissions`      | Allow `Bash(erk:*)` commands in Claude Code         |
| `erk-hooks`                 | Configure Claude Code hooks for session management  |
| `erk-impl-workflow`         | GitHub Action for automated implementation          |
| `fake-driven-testing`       | 5-layer test architecture with fakes                |
| `learn-workflow`            | GitHub Action for automated documentation learning  |
| `learned-docs`              | Autolearning documentation system                   |
| `ruff-format`               | Auto-format Python files with ruff after Write/Edit |
| `tripwires-reminder`        | Remind agent to check tripwires.md                  |
| `tripwires-review`          | Tripwire code review (via convention-based system)  |

**User capabilities** (local to each developer):

| Capability          | Description                                   |
| ------------------- | --------------------------------------------- |
| `shell-integration` | Shell wrapper for seamless worktree switching |
| `statusline`        | Claude Code status line configuration         |

Install a capability with:

```bash
erk init capability add <capability-name>
```

## Init Flags

| Flag               | Purpose                                      |
| ------------------ | -------------------------------------------- |
| `--no-interactive` | Skip all prompts (use defaults)              |
| `-f, --force`      | Overwrite existing repo config               |
| `--shell`          | Show shell integration setup only            |
| `--statusline`     | Configure erk-statusline in Claude Code only |

## Troubleshooting

- Permission errors on `.claude/settings.json` — Check file permissions, or edit manually
- Artifact sync failures — Non-fatal; run `erk artifact sync` to retry
- Global config issues — Check `~/.erk/` directory exists and is writable

## See Also

- [Installation](installation.md) — Basic erk setup
- [Shell Integration](shell-integration.md) — Seamless worktree switching
