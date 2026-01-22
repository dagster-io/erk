---
title: Local Command Patterns
read_when:
  - "designing local commands"
  - "understanding local command taxonomy"
  - "creating audit or assessment commands"
---

# Local Command Patterns

Local commands (`.claude/commands/local/`) are agent instruction files that extend Claude Code with project-specific capabilities. This document describes the patterns and taxonomy for erk local commands.

## Command Categories

### Batch Audit Commands

Batch audit commands scan the repository comprehensively and categorize multiple items:

| Command           | Scope              | Purpose                             |
| ----------------- | ------------------ | ----------------------------------- |
| `/audit-branches` | All branches/PRs   | Identify stale branches and cleanup |
| `/audit-plans`    | All open erk-plans | Identify stale or completed plans   |

**Characteristics:**

- Multi-phase workflow with data collection and analysis
- Presents categorized tables of results
- User selects items to act upon
- Higher context cost (reads many items)

### Single-Item Assessment Commands

Single-item assessment commands analyze one specific item in detail:

| Command            | Input        | Purpose                                       |
| ------------------ | ------------ | --------------------------------------------- |
| `/check-relevance` | Issue number | Assess if PR/plan work is already implemented |

**Characteristics:**

- Focused, inline during development workflow
- Evidence-based verdict with classification
- Lower context cost (single item analysis)
- Immediate actionability

## Design Decision: When to Use Each Pattern

**Use batch audit when:**

- Periodic cleanup operations
- Comprehensive repository health checks
- User needs to see "big picture" of staleness

**Use single-item assessment when:**

- User is actively working on or reviewing specific item
- Quick decision needed during development flow
- Deep analysis of one item is more valuable than broad scan

## Related Documentation

- [Plan Lifecycle](../planning/lifecycle.md) - Plan states and transitions
