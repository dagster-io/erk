# Developer Onboarding

> **Audience**: This guide is for developers joining a repository that already has erk configured. If you're a project maintainer setting up erk for the first time, see [Project Setup](project-setup.md) instead.

## Prerequisites

Before you begin, ensure you have:

- **erk CLI installed** - Follow the [erk installation guide](../../README.md) if needed
- **Claude Code** - The AI-powered CLI that erk extends
- **Graphite CLI** (if your team uses stacked PRs) - Run `gt auth` after installing to authenticate

## Step 1: Clone the Repository

Clone the repository as usual:

```bash
git clone <repo-url>
cd <repo-name>
```

Since erk is already configured by the project maintainer, you'll find:

- **`erk.toml`** - Project configuration
- **`.claude/`** - Kit artifacts (commands, skills, hooks)

These are committed to git and ready to use.

## Step 2: Run Erk Doctor

Run the doctor command to check your setup and identify any issues:

```bash
erk doctor
```

This will verify your environment and report any problems that need attention.

### Shell Integration (Important)

For the best experience, set up shell integration so you can navigate between worktrees seamlessly. This is the most important setup step and needs to be done once per developer.

**Option A: Append directly to your shell config**

```bash
erk shell-init >> ~/.zshrc  # or ~/.bashrc for bash users
```

**Option B: Copy and paste manually**

Run `erk shell-init` to see the shell integration code, then copy and paste it into your `~/.zshrc` (or `~/.bashrc`).

After adding shell integration, restart your shell or run `source ~/.zshrc`.

Run `erk doctor` again to confirm all checks pass.

## Quick Start: Common Erk Commands

Once set up, here are the commands you'll use most:

### Working with Worktrees

```bash
# Create a new worktree for a feature
erk wt create my-feature

# List all worktrees
erk wt list

# Switch to a worktree
erk wt go my-feature

# Delete a worktree when done
erk wt delete my-feature
```

### Working with Plans

```bash
# Create a plan from a GitHub issue
erk plan create --issue 123

# Implement a plan (run inside Claude Code)
/erk:plan-implement
```

### Checking Status

```bash
# See overall erk status
erk status

# Check stack status (if using Graphite)
erk stack status
```

## Troubleshooting

### "erk.toml not found"

You're not in a directory with erk configured. Either:

- Navigate to the repository root
- Ensure the repo has erk configured (see [Project Setup](project-setup.md))

### Kits not loading

Try syncing kits:

```bash
erk kit sync --force
```

### Claude Code doesn't recognize erk commands

Restart your Claude Code session after installing kits.
