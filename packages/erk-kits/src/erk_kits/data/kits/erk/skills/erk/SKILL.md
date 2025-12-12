---
name: erk
description: This skill should be used when working with erk for git worktree management and parallel development. Use when users mention erk commands, worktree workflows, parallel feature development, or when dealing with multiple branches simultaneously. Essential for understanding erk's mental model, command structure, and integration with Graphite for stacked PRs.
---

# Erk

## Overview

Erk is a CLI tool that manages git worktrees in a centralized location with automatic environment setup and integration with Graphite. This skill provides comprehensive guidance for using erk to enable parallel development without branch switching, including configuration, workflow patterns, and command reference.

## When to Use This Skill

Invoke this skill when users:

- Mention erk commands or worktree management
- Ask about parallel feature development or working on multiple branches
- Need help with erk configuration or setup
- Want to understand the erk mental model or directory structure
- Ask about integrating erk with Graphite for stacked diffs
- Need guidance on cleanup or maintenance workflows
- Request help with environment isolation across worktrees

## Core Concepts

Before providing guidance, understand these key concepts:

**Worktree vs Erk:**

- **Worktree**: Git's native feature for multiple working directories
- **Erk**: A configured worktree with environment setup and tooling integration

**Directory Structure:**

```
~/erks/                    ← Erks root (configurable)
├── repo-name/                  ← Work dir (per repo)
│   ├── config.toml             ← Repo-specific config
│   ├── feature-a/              ← Individual erk
│   │   ├── .env                ← Auto-generated env vars
│   │   └── .PLAN.md            ← Optional plan file (gitignored)
│   └── feature-b/              ← Another erk
└── other-repo/                 ← Work dir for another repo
```

**Key Insight**: Worktrees are identified by **name** (directory), not branch name.

## Using the Reference Documentation

When providing erk guidance, load the comprehensive reference documentation:

```
references/erk.md
```

This reference contains:

- Complete mental model and terminology
- Full command reference with examples
- Configuration patterns and presets
- Workflow patterns for common scenarios
- Integration details (Git, Graphite, GitHub)
- Architecture insights for contributors
- Practical examples for daily development

**Loading Strategy:**

- Always load `references/erk.md` when user asks erk-related questions
- The reference is comprehensive (~1200 lines) but optimized for progressive reading
- Use grep patterns to find specific sections when needed:
  - `erk create` - Creating worktrees
  - `erk checkout` - Navigating to branches
  - `erk dash` - Plan dashboard
  - `Pattern [0-9]:` - Workflow patterns
  - `Graphite Integration` - Graphite-specific features
  - `Configuration` - Setup and config

## Common Operations

When users ask for help with erk, guide them using these patterns:

### First-Time Setup

1. Check if erk is initialized: `erk config list`
2. If not initialized: `erk init` (sets up global + repo config)
3. Consider using presets: `erk init --preset dagster` or `--preset auto`
4. Set up shell integration: `erk init --shell` (enables `ws` command)

### Creating Worktrees

Load `references/erk.md` and search for "erk create" section to provide:

- Syntax options (basic, custom branch, from existing branch, with plan file)
- Environment setup details
- Post-create command execution

### Navigating to Branches

Load `references/erk.md` and search for "erk checkout" section to provide:

- Navigate to branch: `erk checkout <branch>` to find and navigate to a branch
- Navigate with options: `erk checkout <branch> --auto-create` to create worktree if needed
- Stack navigation: Use Graphite's `gt up` and `gt down` for stack traversal
- Environment activation details

### Plan Dashboard

Load `references/erk.md` and search for "erk dash" section to provide:

- Basic dashboard: `erk dash`
- With PR info: `erk dash --prs`
- With workflow runs: `erk dash --runs`
- Show all columns: `erk dash --all` or `erk dash -a`

### Cleanup and Maintenance

Load `references/erk.md` for cleanup guidance:

- Manual deletion: `erk delete <name>`

## Workflow Guidance

When users describe their workflow needs, map them to patterns in the reference:

**Pattern 1: Basic Feature Development** - Standard parallel development
**Pattern 2: Plan-Based Development** - Separation of planning and implementation with `.PLAN.md`
**Pattern 3: Existing Branches** - Creating worktrees from existing work
**Pattern 4: Stacked Development** - Using Graphite for dependent features
**Pattern 5: Parallel Development** - Managing multiple concurrent features
**Pattern 7: Cleanup After Merging** - Post-PR maintenance
**Pattern 8: Environment-Specific** - Unique environments per worktree

Load the appropriate pattern sections from `references/erk.md` based on user needs.

## Configuration Guidance

When users need configuration help:

1. Load the Configuration section from `references/erk.md`
2. Distinguish between global config (`~/.erk/config.toml`) and repo config (`{work_dir}/config.toml`)
3. Explain template variables: `{worktree_path}`, `{repo_root}`, `{name}`
4. Guide through environment variables and post-create commands
5. Suggest appropriate presets if applicable

## Integration Guidance

### Graphite Integration

When users mention Graphite or stacked diffs:

- Load the Graphite Integration section from `references/erk.md`
- Explain stack navigation: Use Graphite's `gt up` and `gt down` commands
- Show stack visualization: `erk list --stacks`
- Branch navigation: `erk checkout <branch>` to navigate to any branch in the stack
- Reference the separate Graphite (gt) documentation for deeper gt concepts

### GitHub Integration

When users need PR status information:

- Load the GitHub Integration section from `references/erk.md`
- Explain PR status indicators in listings
- Note requirement for `gh` CLI

## Architecture for Contributors

When users want to contribute to erk or understand its internals:

- Load the "Key Insights for AI Agents" section from `references/erk.md`
- Explain the 3-layer architecture (Commands → Core Logic → Operations)
- Cover dependency injection pattern with ABC interfaces
- Show testing guidelines with fakes
- Reference additional internal documentation files mentioned in the reference

## Resources

### references/

- `erk.md` - Comprehensive erk mental model and command reference (~1200 lines)

This reference should be loaded whenever providing erk guidance to ensure accurate, detailed information.
