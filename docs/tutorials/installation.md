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

Run init from your project's root directory:

```bash
erk init
```

Init follows a three-step process:

### Step 1: Repository Verification

Verifies you're in a git repository with a valid configuration.

### Step 2: Project Configuration

Creates two configuration files:

**Global config** (`~/.erk/config.json`) — user-specific settings:

- `erk_root`: Where worktrees are created (default: `~/.erk/repos/<repo>/worktrees/`)
- `use_graphite`: Auto-detected if `gt` is installed

**Repo config** (`.erk/config.toml`) — repository settings that should be committed:

- Required capabilities (e.g., hooks)
- Post-create hooks for worktree setup
- Environment variables for Claude sessions

**Interactive prompts:**

- **Gitignore**: Add `.env`, `.erk/scratch/`, `.impl/` to `.gitignore`?
- **Claude permissions**: Add `erk` commands to `.claude/settings.json`?
- **Shell integration**: Show setup instructions for directory switching?
- **Plans repo labels**: Create `erk-plan` label in GitHub?

Use `--no-interactive` to skip prompts and accept defaults.

**Artifact syncing:**

Init syncs Claude Code artifacts to your `.claude/` directory:

- Commands (`/erk:plan-save`, `/erk:pr-submit`, etc.)
- Skills (coding standards, documentation patterns)
- Agents (devrun for test/lint execution)

These artifacts enable erk's AI-assisted workflows in Claude Code.

### Step 3: Optional Enhancements

Shows capability status and offers optional features:

```
Capabilities:
  ✅ hooks (installed)

Optional capabilities available:
  Run 'erk init capability list' to see all options
```

**Important flags:**

| Flag               | Purpose                                      |
| ------------------ | -------------------------------------------- |
| `--no-interactive` | Skip all prompts (use defaults)              |
| `-f, --force`      | Overwrite existing repo config               |
| `--shell`          | Show shell integration setup only            |
| `--statusline`     | Configure erk-statusline in Claude Code only |

**Files created:**

| File                    | Committed? | Purpose                       |
| ----------------------- | ---------- | ----------------------------- |
| `~/.erk/config.json`    | No         | Global user settings          |
| `.erk/config.toml`      | Yes        | Repository configuration      |
| `.claude/commands/erk/` | Yes        | Claude Code commands          |
| `.claude/skills/`       | Yes        | Coding standards and patterns |
| `.claude/agents/`       | Yes        | Agent definitions             |
| `.erk/prompt-hooks/`    | Yes        | Custom hook configurations    |

**Troubleshooting:**

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
