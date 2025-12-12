# Developer Onboarding

> **Audience**: This guide is for developers joining a repository that already has erk configured. If you're a project maintainer setting up erk for the first time, see [Project Setup](project-setup.md) instead.

## Prerequisites

Before you begin, ensure you have:

- **erk CLI installed** - Follow the [erk installation guide](../../README.md) if needed
- **Claude Code** - The AI-powered CLI that erk extends

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

## Step 2: Verify Your Setup

Check that erk recognizes the project configuration:

```bash
erk status
```

You should see your project configuration displayed.

## Step 3: Install Kits (Optional)

If the project uses kits that aren't bundled, you may need to install them:

```bash
erk kit list  # See what's available
erk kit sync  # Sync any kits specified in erk.toml
```

## Step 4: Graphite Setup (Optional)

If your team uses Graphite for stacked PRs:

```bash
# Authenticate with Graphite
gt auth

# Initialize Graphite in the repo (if not already done)
gt init
```

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
