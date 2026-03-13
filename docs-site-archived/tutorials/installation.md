# Installation

Install erk and verify your setup.

**Prerequisites:** Complete [Prerequisites](prerequisites.md) first—you need Python 3.11+, Claude Code, uv, and GitHub CLI.

## Install erk

Install erk as a project dependency:

```bash
cd your-project
uv add erk
uv sync
```

**Verify the installation:**

```bash
# In your project directory (with venv activated)
erk --version
```

You should see output like `erk 0.7.x`.

**Troubleshooting:**

- `uv: command not found` — Install uv first. See [Prerequisites](prerequisites.md#uv-python-package-manager).
- Python version error — erk requires Python 3.11 or higher. Check with `python --version`.
- `erk: command not found` — Make sure your venv is activated (`. .venv/bin/activate`) or use `.venv/bin/erk` directly.

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

2. **User setup** (one-time per developer) — Creates local configuration on each developer's machine. This includes the global config file.

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

The first time you run `erk init` (in any repo), it creates your global config. Subsequent runs in other repos skip this step.

For optional capabilities (devrun, dignified-python, etc.), init flags, and troubleshooting, see [Advanced Configuration](advanced-configuration.md).

## Quick Reference

| Task                | Command                 |
| ------------------- | ----------------------- |
| Install erk         | `uv add erk && uv sync` |
| Check version       | `erk --version`         |
| Verify setup        | `erk doctor`            |
| Verbose diagnostics | `erk doctor --verbose`  |
| Initialize repo     | `erk init`              |
| Update erk          | `uv upgrade erk`        |

## Next Steps

- [Your First Plan](first-plan.md) — Create your first plan and land a PR
