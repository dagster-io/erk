---
title: Parallel State Checks
read_when:
  - "checking implementation state"
  - "reading multiple files for context"
  - "optimizing session flow"
---

# Parallel State Checks

## Pattern

When checking implementation state, issue multiple independent tool calls in parallel:

```
// Single response with multiple calls:
- Read .impl/plan.md
- Read .impl/plan-ref.json
- Bash: ls -la .impl/
- Bash: git branch --show-current
```

## When to Use

- Reading multiple unrelated files
- Checking multiple status indicators
- Gathering context before decisions

## Benefit

Reduces round-trip latency when information gathering is independent.
