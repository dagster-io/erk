---
title: Async Agent Work Patterns
read_when:
  - "launching async subagents"
  - "managing parallel work during implementations"
  - "optimizing agent efficiency"
---

# Async Agent Work Patterns

Don't idle while async agents run.

## Pattern

After launching an async subagent (e.g., libcst-refactor):

1. Immediately start parallel work
2. Read files for manual edits
3. Plan next steps
4. Only block when you've exhausted independent work

## Anti-Pattern

Launching an async agent, then waiting with `TaskOutput(block=true)` immediately. This wastes time that could be used for parallel investigation.
