# `erk` Documentation

**erk** is a CLI tool for plan-oriented agentic engineering—a workflow where AI agents create implementation plans, execute them in isolated worktrees, and ship code via automated PR workflows.

For the philosophy and design principles behind erk, see [The TAO of erk](TAO.md).

## The Composability Model

Erk is designed for incremental adoption. Start with the core workflow and add capabilities as you need them:

| Layer | Name                   | What It Adds                                     |
| ----- | ---------------------- | ------------------------------------------------ |
| 0     | **Core Workflow**      | Plan → save → implement → review → land          |
| 1     | **Worktree Isolation** | Parallel agent execution in separate directories |
| 2     | **Stacked PRs**        | Graphite-based dependent PR chains               |
| 3     | **Remote Execution**   | GitHub Actions for sandboxed, scalable dispatch  |
| 4     | **Objectives**         | Multi-plan coordination toward larger goals      |

Start with Layer 0. Add layers when you need them.

## Getting Started

New to erk? Start here:

1. [Prerequisites](tutorials/prerequisites.md) - Tools you need installed
2. [Installation](tutorials/installation.md) - Install and configure erk
3. [Your First Plan](tutorials/first-plan.md) - Complete tutorial from plan to PR
4. [Advanced Configuration](tutorials/advanced-configuration.md) - Customize erk for your workflow

## Layer-by-Layer Guide

### Layer 0: The Core Workflow

The plan-first loop that everything else builds on. An agent creates an implementation plan, saves it as a GitHub draft PR, implements the plan in code, and submits for review. This is the only layer you need to start shipping with erk.

- [The Workflow](topics/the-workflow.md) - Full walkthrough of the plan → PR lifecycle
- [Use the Local Workflow](howto/local-workflow.md) - Plan, implement, and ship locally
- [Work Without Plans](howto/planless-workflow.md) - Quick changes without formal plans
- [Checkout and Sync PRs](howto/pr-checkout-sync.md) - Review and iterate on PRs
- [Automatic Merge Conflict Resolution](howto/conflict-resolution.md) - Handle merge conflicts with AI assistance

### Layer 1: Worktree Isolation

Run multiple agents in parallel, each in its own isolated git worktree. No branch switching, no stashing—every implementation gets a clean working directory.

- [Worktrees](topics/worktrees.md) - How erk uses git worktrees for isolation
- [Navigate Branches and Worktrees](howto/navigate-branches-worktrees.md) - Move between worktrees

### Layer 2: Stacked PRs

Chain dependent PRs together with Graphite so reviewers see focused, incremental diffs instead of one massive PR.

- [Graphite Integration](tutorials/graphite-integration.md) - Set up and use stacked PR workflows

### Layer 3: Remote Execution

Dispatch implementations to GitHub Actions for sandboxed, scalable execution. Useful for running untrusted agents or parallelizing work across multiple plans.

- [Run Remote Execution](howto/remote-execution.md) - Dispatch to GitHub Actions
- [Test Workflows](howto/test-workflows.md) - Test CI and dispatch workflows

### Layer 4: Objectives

Coordinate multiple plans toward a larger goal. Objectives track progress across related PRs and provide a high-level view of multi-plan work. _(Docs coming in a future phase.)_

## Other Documentation

| Directory         | Audience     | Purpose                                  |
| ----------------- | ------------ | ---------------------------------------- |
| `docs/learned/`   | AI agents    | Agent-generated patterns and conventions |
| `docs/developer/` | Contributors | Internal development docs                |
