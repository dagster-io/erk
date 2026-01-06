# Erk Documentation

**erk** is a CLI tool for plan-oriented agentic engineering—a workflow where AI agents create implementation plans, execute them in isolated worktrees, and ship code via automated PR workflows.

For the philosophy and design principles behind erk, see [The TAO of erk](../TAO.md).

## Quick Start

New to erk? Start here:

1. [Prerequisites](tutorials/prerequisites.md) - Tools you need installed
2. [Installation](tutorials/installation.md) - Install and configure erk
3. [Your First Plan](tutorials/first-plan.md) - Complete tutorial from plan to PR

## Documentation Sections

### [Tutorials](tutorials/)

Step-by-step lessons to get you started.

- [Prerequisites](tutorials/prerequisites.md) - Required tools and versions
- [Installation](tutorials/installation.md) - Installing and initializing erk
- [Your First Plan](tutorials/first-plan.md) - End-to-end tutorial
- [Shell Integration](tutorials/shell-integration.md) - Terminal setup for directory switching

### [Topics](topics/)

Core concepts that explain how erk works.

- [Worktrees](topics/worktrees.md) - Parallel development with git worktrees
- [Stacked PRs](topics/stacked-prs.md) - Building changes incrementally with Graphite
- [Plan Mode](topics/plan-mode.md) - Claude Code's planning workflow
- [The Workflow](topics/the-workflow.md) - From idea to merged PR
- [Plan-Oriented Engineering](topics/plan-oriented-engineering.md) - The philosophy behind erk

### [How-to Guides](howto/)

Task-focused recipes for specific goals.

- [Use the Local Workflow](howto/local-workflow.md) - Plan, implement, and ship locally
- [Run Remote Execution](howto/remote-execution.md) - Run implementations in GitHub Actions
- [Checkout and Sync PRs](howto/pr-checkout-sync.md) - Review and iterate on PRs
- [Resolve Merge Conflicts](howto/conflict-resolution.md) - Handle merge conflicts with AI assistance
- [Work Without Plans](howto/planless-workflow.md) - Quick changes without formal plans
- [Extract Documentation](howto/documentation-extraction.md) - Capture patterns for future agents

### [Reference](ref/)

Complete technical reference.

- [CLI Command Reference](ref/commands.md) - All CLI commands
- [Slash Command Reference](ref/slash-commands.md) - Claude Code slash commands
- [Configuration Reference](ref/configuration.md) - Config files and options
- [File Location Reference](ref/file-locations.md) - Where erk stores data

### [FAQ](faq/)

Common questions and solutions.

- [Shell Integration](faq/shell-integration.md) - Directory switching problems
- [Graphite Issues](faq/graphite-issues.md) - Stack and sync problems
- [General](faq/general.md) - Frequently asked questions

## Common User Journeys

**"I want to start using erk"**
→ [Prerequisites](tutorials/prerequisites.md) → [Installation](tutorials/installation.md) → [Your First Plan](tutorials/first-plan.md)

**"I want to understand how erk works"**
→ [The Workflow](topics/the-workflow.md) → [Plan-Oriented Engineering](topics/plan-oriented-engineering.md)

**"I'm reviewing a teammate's PR"**
→ [Checkout and Sync PRs](howto/pr-checkout-sync.md)

**"My rebase has conflicts"**
→ [Resolve Merge Conflicts](howto/conflict-resolution.md)

**"I need quick iteration without planning"**
→ [Work Without Plans](howto/planless-workflow.md)

## Other Documentation

| Directory                     | Audience     | Purpose                                  |
| ----------------------------- | ------------ | ---------------------------------------- |
| [docs/learned/](learned/)     | AI agents    | Agent-generated patterns and conventions |
| [docs/developer/](developer/) | Contributors | Internal development docs                |
