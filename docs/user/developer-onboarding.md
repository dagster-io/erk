# Developer Onboarding

> **Audience**: This guide is for developers joining a repository that already has erk configured. If you're a project maintainer setting up erk for the first time, see [Project Setup](project-setup.md) instead.

## Overview

The main goal of developer onboarding is to set up **shell integration**, which is a per-developer configuration. Shell integration enables critical erk workflow features like seamless worktree navigation.

## Prerequisites

Before you begin, ensure you have:

- **Git repository cloned** - You should already have the repo on your machine
- **erk CLI installed** - Follow the [erk installation guide](../../README.md) if needed
- **Claude Code** - The AI-powered CLI that erk extends
- **Graphite CLI** (if your team uses stacked PRs) - Run `gt auth` after installing to authenticate

Since erk is already configured by the project maintainer, you'll find:

- **`erk.toml`** - Project configuration
- **`.claude/`** - Kit artifacts (commands, skills, hooks)

These are committed to git and ready to use.

## Shell Integration

Set up shell integration so you can navigate between worktrees seamlessly. This is the most important setup step and needs to be done once per developer.

**Option A: Append directly to your shell config**

```bash
erk shell-init >> ~/.zshrc  # or ~/.bashrc for bash users
```

**Option B: Copy and paste manually**

Run `erk shell-init` to see the shell integration code, then copy and paste it into your `~/.zshrc` (or `~/.bashrc`).

After adding shell integration, restart your shell or run `source ~/.zshrc`.

## Verify Your Setup

Run the doctor command to verify everything is configured correctly:

```bash
erk doctor
```

All checks should pass. If any issues are reported, follow the guidance to resolve them.

## Troubleshooting

### "erk.toml not found"

You're not in a directory with erk configured. Either:

- Navigate to the repository root
- Ensure the repo has erk configured (see [Project Setup](project-setup.md))

### Kits not loading

Try reinstalling kits:

```bash
erk kit install <kit-id> --force
```

### Claude Code doesn't recognize erk commands

Restart your Claude Code session after installing kits.
