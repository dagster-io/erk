# Erk Documentation

**erk** is a CLI tool for plan-oriented agentic engineering—a workflow where AI agents create implementation plans, execute them in isolated worktrees, and ship code via automated PR workflows.

For the philosophy and design principles behind erk, see [The TAO of erk](../TAO.md).

## Quick Start

New to erk? Start here:

1. [Prerequisites](getting-started/prerequisites.md) - Tools you need installed
2. [Installation](getting-started/installation.md) - Install and configure erk
3. [Your First Plan](getting-started/first-plan.md) - Complete tutorial from plan to PR

## Documentation Sections

### [Getting Started](getting-started/)

Setup guides and your first steps with erk.

- [Prerequisites](getting-started/prerequisites.md) - Required tools and versions
- [Installation](getting-started/installation.md) - Installing and initializing erk
- [Your First Plan](getting-started/first-plan.md) - End-to-end tutorial
- [Shell Integration](getting-started/shell-integration.md) - Terminal setup for directory switching

### [Concepts](concepts/)

Core ideas that make erk work.

- [Worktrees](concepts/worktrees.md) - Parallel development with git worktrees
- [Stacked PRs](concepts/stacked-prs.md) - Building changes incrementally with Graphite
- [Plan Mode](concepts/plan-mode.md) - Claude Code's planning workflow
- [The Workflow](concepts/the-workflow.md) - From idea to merged PR
- [Plan-Oriented Engineering](concepts/plan-oriented-engineering.md) - The philosophy behind erk

### [Guides](guides/)

Step-by-step workflows for common tasks.

- [Local Workflow](guides/local-workflow.md) - Plan, implement, and ship locally
- [Remote Execution](guides/remote-execution.md) - Run implementations in GitHub Actions
- [PR Checkout & Sync](guides/pr-checkout-sync.md) - Review and iterate on PRs
- [Conflict Resolution](guides/conflict-resolution.md) - Handle merge conflicts with AI assistance
- [Planless Workflow](guides/planless-workflow.md) - Quick changes without formal plans
- [Documentation Extraction](guides/documentation-extraction.md) - Capture patterns for future agents

### [Reference](reference/)

Complete command and configuration reference.

- [Commands](reference/commands.md) - All CLI commands
- [Slash Commands](reference/slash-commands.md) - Claude Code slash commands
- [Configuration](reference/configuration.md) - Config files and options
- [File Locations](reference/file-locations.md) - Where erk stores data

### [Troubleshooting](troubleshooting/)

Common issues and solutions.

- [Shell Integration](troubleshooting/shell-integration.md) - Directory switching problems
- [Graphite Issues](troubleshooting/graphite-issues.md) - Stack and sync problems
- [FAQ](troubleshooting/faq.md) - Frequently asked questions

## Common User Journeys

**"I want to start using erk"**
→ [Prerequisites](getting-started/prerequisites.md) → [Installation](getting-started/installation.md) → [Your First Plan](getting-started/first-plan.md)

**"I want to understand how erk works"**
→ [The Workflow](concepts/the-workflow.md) → [Plan-Oriented Engineering](concepts/plan-oriented-engineering.md)

**"I'm reviewing a teammate's PR"**
→ [PR Checkout & Sync](guides/pr-checkout-sync.md)

**"My rebase has conflicts"**
→ [Conflict Resolution](guides/conflict-resolution.md)

**"I need quick iteration without planning"**
→ [Planless Workflow](guides/planless-workflow.md)

## Other Documentation

| Directory                     | Audience     | Purpose                                  |
| ----------------------------- | ------------ | ---------------------------------------- |
| [docs/learned/](learned/)     | AI agents    | Agent-generated patterns and conventions |
| [docs/developer/](developer/) | Contributors | Internal development docs                |
