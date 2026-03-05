---
title: Plan-oriented engineering
description: Why plans are the unit of work in erk
sidebar:
  order: 1
---

Plan-oriented engineering is the core philosophy behind erk. Every code change begins with a **plan** — a structured document that describes what to build, why, and how.

## Plans as documents

A plan is a markdown document stored as a GitHub draft PR. It contains:

- **Summary** of the change
- **Context** the implementing agent needs (API quirks, architectural constraints, pitfalls)
- **Implementation phases** broken into sequential steps
- **Success criteria** defining what "done" looks like

Plans are not tickets or issues. They are **implementation instructions** written for an AI agent. The level of detail matters: a good plan includes the specific files to modify, the patterns to follow, and the edge cases to handle.

## Why plans work

Traditional development asks you to hold the entire implementation in your head. You write code, run into problems, adjust, and eventually ship. This works for small changes but breaks down when:

- Multiple agents work on a codebase simultaneously
- Changes span many files and require coordination
- You want to delegate implementation while maintaining quality

Plans solve this by **separating the thinking from the doing**. You invest time upfront to think through the approach, then hand off execution to an agent that follows the plan mechanically.

## Worktree isolation

Each plan executes in its own git worktree. This means:

- The agent's changes never touch your working directory
- Multiple plans can run in parallel without conflicts
- Failed implementations are discarded cleanly
- You can review changes in isolation before merging

## The plan lifecycle

```
Draft  -->  Saved  -->  Implementing  -->  Submitted  -->  Landed
```

1. **Draft**: You write the plan (or an agent drafts it in plan mode)
2. **Saved**: The plan is stored as a GitHub draft PR
3. **Implementing**: An agent is actively working on the plan in a worktree
4. **Submitted**: The PR is ready for review with implementation complete
5. **Landed**: The PR is merged and the worktree is cleaned up

## Stacking plans

Plans can depend on each other. Erk integrates with Graphite to manage **stacked PRs** — a sequence of dependent changes that land in order. This lets you break large features into reviewable increments while maintaining dependencies.
