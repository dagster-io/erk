---
title: Local workflow
description: Day-to-day usage of erk for plan-oriented development
sidebar:
  order: 1
---

This guide walks through the typical erk workflow: creating plans, implementing them, and shipping PRs.

## Prerequisites

- Python 3.10+ with [uv](https://docs.astral.sh/uv/) installed
- Git with worktree support
- GitHub CLI (`gh`) authenticated
- Claude Code (for AI-assisted plan creation and implementation)

## Creating a plan

Start by entering plan mode in Claude Code. Describe what you want to build, and the agent will draft a structured plan with phases, context, and success criteria.

```bash
# In Claude Code, use plan mode to draft a plan
# The agent creates a structured markdown document
```

Once satisfied, save the plan to GitHub:

```
/erk:plan-save
```

This creates a draft PR containing the plan. The PR number becomes the plan's identifier.

## Implementing a plan

To implement a saved plan:

```
/erk:plan-implement 1234
```

This command:

1. Fetches the plan from GitHub
2. Creates or checks out a feature branch
3. Sets up the implementation context
4. Executes each phase sequentially
5. Runs CI checks
6. Submits the PR for review

## Dispatching for remote implementation

For plans you want to run autonomously:

```bash
erk pr dispatch 1234
```

This sends the plan to a remote agent for implementation. You can continue working on other tasks while the agent executes the plan in the background.

## Listing open plans

```bash
erk pr list
```

Shows all open plans with their status (draft, implementing, submitted).

## Working with worktrees

Erk manages git worktrees automatically. Each plan gets its own worktree, so your working directory stays clean.

```bash
# List active worktrees
erk wt list

# Check out a plan's worktree
source "$(erk pr checkout 1234 --script)"
```

## Iterating on a plan

If implementation reveals issues with the plan, you can replan:

```
/erk:replan
```

This updates the plan based on what was learned during implementation, preserving the original context while adjusting the approach.
