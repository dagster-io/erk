---
title: Introduction
description: What erk is and why it exists
sidebar:
  order: 1
---

Erk is a CLI tool for **plan-oriented agentic engineering**: a workflow where AI agents create implementation plans, execute them in isolated worktrees, and ship code through automated PR workflows.

## The problem

AI coding assistants produce better results when they have clear instructions. Without structure, agents wander through codebases, make inconsistent changes, and lose context. The feedback loop between "tell the AI what to do" and "get working code" is slow and unpredictable.

## The approach

Erk introduces a **plan** as the unit of work. Instead of asking an agent to "fix the login bug," you create a plan that describes the problem, the approach, the files involved, and the success criteria. The agent implements the plan in an isolated worktree and submits a PR.

This approach gives you:

- **Reproducibility** - Plans are documents. You can review, revise, and re-execute them.
- **Isolation** - Each plan runs in its own worktree. No conflicts with your working directory.
- **Parallelism** - Multiple agents can implement different plans simultaneously.
- **Traceability** - Every PR links back to its plan. You can see exactly what was requested and what was delivered.

## Core workflow

```
Plan  -->  Worktree  -->  Implement  -->  CI  -->  PR
```

1. **Create a plan** describing the change you want
2. **Erk allocates a worktree** for isolated implementation
3. **An agent implements** the plan following its instructions
4. **CI runs** to validate the changes
5. **A PR is submitted** linking back to the plan

## What's next

- [Concepts: Plan-oriented engineering](/concepts/01-plan-oriented-engineering/) explains the philosophy behind the workflow
- [Guides: Local workflow](/guides/01-local-workflow/) walks through using erk day-to-day
- [Reference: CLI](/reference/01-cli/) documents every command
