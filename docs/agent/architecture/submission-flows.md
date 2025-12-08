---
title: "Submission Flow Comparison: Git vs Graphite"
read_when:
  - "choosing between git and Graphite PR submission"
  - "understanding PR workflow differences"
  - "comparing submission architectures"
  - "deciding which submission flow to use"
---

# Submission Flow Comparison: Git vs Graphite

This document compares the two PR submission workflows available in erk.

## Overview

| Aspect          | Git Flow (`/git:pr-push`) | Graphite Flow (`/gt:pr-submit`) |
| --------------- | ------------------------- | ------------------------------- |
| Tool            | git + gh CLI              | Graphite (gt)                   |
| Stack support   | None                      | Full stack management           |
| Commit handling | Preserves history         | Squashes & rebases              |
| Use case        | Any repo, CI automation   | Graphite-enabled repos          |

## Architecture Comparison

### Graphite Flow (Python-based)

```
Slash Command → Preflight (Python) → AI Analysis → Finalize (Python)
```

- **Preflight**: Auth checks, squash commits, gt submit, get diff
- **AI Analysis**: Diff analysis, commit message generation
- **Finalize**: Update PR metadata, amend commit

### Git Flow (Currently Agent-based)

```
Slash Command → Agent (all orchestration in markdown)
```

- Single agent handles everything: auth, stage, push, PR creation, etc.
- No Python layer for testability
- Target: Align with Graphite's two-phase pattern

## Shared Infrastructure

Both flows share:

- `build_pr_body_footer()` from `erk_shared.github.pr_footer`
- Issue reference handling via `.impl/issue.json`
- `post-pr-comment` kit CLI command

## When to Use Each

- **Git flow**: CI automation, repos without Graphite, simple submissions
- **Graphite flow**: Local development with stack management, dependent PRs
