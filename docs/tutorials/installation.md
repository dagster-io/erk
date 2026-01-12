# Installation

Install erk and verify your setup.

**Prerequisites:** Complete [Prerequisites](prerequisites.md) first—you need Python 3.11+, Claude Code, uv, and GitHub CLI.

## Install erk

Install erk as a global CLI tool using uv:

```bash
uv tool install erk
```

**Why `uv tool install`?**

This installs erk as a system-wide CLI command, isolated from your project environments:

- **Global availability**: Run `erk` from any directory
- **Isolated environment**: Won't conflict with your project dependencies
- **Easy updates**: Use `uv tool upgrade erk` to update

**Verify the installation:**

```bash
erk --version
```

You should see output like `erk 0.4.x`.

**Troubleshooting:**

- `uv: command not found` — Install uv first. See [Prerequisites](prerequisites.md#uv-python-package-manager).
- Python version error — erk requires Python 3.11 or higher. Check with `python --version`.
- Permission errors — Try `uv tool install erk --force` to reinstall.

## Verify Installation

Run the doctor command to check your setup:

```bash
erk doctor
```

Doctor checks two categories:

- **Repository Setup**: Checks specific to the current repo (git, config, hooks)
- **User Setup**: Global prerequisites (CLI tools, authentication)

**Condensed output (default):**

```
🔍 Checking erk setup...

Repository Setup
✅ Git repository (2 checks)
✅ Claude settings (4 checks)
✅ Erk configuration (6 checks)
✅ GitHub (3 checks)
✅ Hooks (1 checks)

User Setup
✅ erk CLI installed: v0.4.7
✅ Claude CLI installed
✅ GitHub CLI installed
✅ uv installed
✅ User checks (4 checks)

✨ All checks passed!
```

**Verbose output (`erk doctor --verbose`):**

Add `--verbose` to see individual checks within each category—useful for debugging failures.

**Status indicators:**

| Icon | Meaning | Action                         |
| ---- | ------- | ------------------------------ |
| ✅   | Passed  | None needed                    |
| ℹ️   | Info    | Optional enhancement available |
| ❌   | Failed  | Fix required before continuing |

**If checks fail:**

- Repository Setup failures — Run `erk init` to configure the repo
- User Setup failures — See [Prerequisites](prerequisites.md) to install missing tools

## Initialize a Repository

Erk initialization has two phases:

1. **Project setup** (one-time per repository) — Creates configuration files and Claude Code artifacts that are committed to the repo. Once done, other team members get erk support automatically.

2. **User setup** (one-time per developer) — Creates local configuration on each developer's machine. This includes the global config file and optional shell integration.

Run init from your project's root directory:

```bash
erk init
```

### What happens during project setup

When you run `erk init` in a repository for the first time, it creates:

- **`.erk/config.toml`** — Repository configuration (commit this)
- **`.erk/required-erk-uv-tool-version`** — Minimum erk version for the project
- **`.claude/commands/erk/`** — Claude Code slash commands like `/erk:plan-save`
- **`.claude/skills/`** — Coding standards and documentation patterns
- **`.claude/agents/`** — Agent definitions (e.g., devrun for test execution)

Once committed, any developer who clones the repo gets these artifacts automatically.

### What happens during user setup

Each developer needs local state that isn't committed:

- **`~/.erk/config.json`** — Global config with:
  - `erk_root`: Where worktrees are created (default: `~/.erk/repos/<repo>/worktrees/`)
  - `use_graphite`: Auto-detected based on whether `gt` is installed
- **Shell integration** (optional) — Enables seamless `cd` behavior when switching worktrees

The first time you run `erk init` (in any repo), it creates your global config. Subsequent runs in other repos skip this step.

### Capabilities

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
| `dignified-review`          | GitHub Action for Python code review                |
| `erk-bash-permissions`      | Allow `Bash(erk:*)` commands in Claude Code         |
| `erk-hooks`                 | Configure Claude Code hooks for session management  |
| `erk-impl-workflow`         | GitHub Action for automated implementation          |
| `fake-driven-testing`       | 5-layer test architecture with fakes                |
| `learn-workflow`            | GitHub Action for automated documentation learning  |
| `learned-docs`              | Autolearning documentation system                   |
| `ruff-format`               | Auto-format Python files with ruff after Write/Edit |
| `tripwires-reminder`        | Remind agent to check tripwires.md                  |
| `tripwires-review`          | GitHub Action for tripwire code review              |

**User capabilities** (local to each developer):

| Capability          | Description                                   |
| ------------------- | --------------------------------------------- |
| `shell-integration` | Shell wrapper for seamless worktree switching |
| `statusline`        | Claude Code status line configuration         |

Install a capability with:

```bash
erk init capability add <capability-name>
```

### Init flags

| Flag               | Purpose                                      |
| ------------------ | -------------------------------------------- |
| `--no-interactive` | Skip all prompts (use defaults)              |
| `-f, --force`      | Overwrite existing repo config               |
| `--shell`          | Show shell integration setup only            |
| `--statusline`     | Configure erk-statusline in Claude Code only |

### Troubleshooting

- Permission errors on `.claude/settings.json` — Check file permissions, or edit manually
- Artifact sync failures — Non-fatal; run `erk artifact sync` to retry
- Global config issues — Check `~/.erk/` directory exists and is writable

## Quick Reference

| Task                    | Command                |
| ----------------------- | ---------------------- |
| Install erk             | `uv tool install erk`  |
| Check version           | `erk --version`        |
| Verify setup            | `erk doctor`           |
| Verbose diagnostics     | `erk doctor --verbose` |
| Initialize repo         | `erk init`             |
| Update erk              | `uv tool upgrade erk`  |
| Shell integration setup | `erk init --shell`     |

## Next Steps

- [Your First Plan](first-plan.md) — Create your first plan and land a PR
- [Shell Integration](shell-integration.md) — Optional: Enable seamless directory switching
