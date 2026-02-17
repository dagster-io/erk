---
title: Parallel Agent Orchestration for Bulk Operations
read_when:
  - "designing parallel agent workflows for bulk operations"
  - "implementing multi-agent batch processing"
  - "understanding how audit-scan or learn commands parallelize work"
tripwires:
  - action: "launching parallel agents that return results inline instead of writing to files"
    warning: "Parallel agents must write results via Write tool to .erk/scratch/ files. Inline results can be truncated or lost. The parent agent reads files after completion."
  - action: "reading parallel agent output without verifying files exist"
    warning: "Always verify output files exist (ls -la) before reading. Agent failures may produce empty or missing files."
---

# Parallel Agent Orchestration for Bulk Operations

When processing many items (auditing docs, analyzing sessions, extracting insights), erk uses parallel Task agents to reduce wall-clock time. This document describes the orchestration pattern.

## The Pattern

<!-- Source: .claude/commands/local/audit-scan.md, Phase 3 -->
<!-- Source: .claude/commands/erk/learn.md, Launch Parallel Analysis Agents -->

1. **Partition work** into batches (round-robin for even distribution)
2. **Launch agents** with `run_in_background: true`
3. **Each agent writes** results to a file via the Write tool
4. **Wait for completion** via `TaskOutput(block: true)`
5. **Verify output files** exist before reading
6. **Aggregate results** from all output files

## Why File-Based Output

Agents write results to `.erk/scratch/` files instead of returning them inline because:

- **Truncation prevention**: Large agent responses can be truncated. File writes preserve full content.
- **Persistence**: Files survive agent context boundaries. If the parent agent's context is summarized, file paths still work.
- **Verification**: Files can be checked for existence and size before processing.

## Batch Partitioning

The `audit-scan` command demonstrates round-robin partitioning:

```
Batch 1: items 0, 5, 10, 15, ...
Batch 2: items 1, 6, 11, 16, ...
Batch 3: items 2, 7, 12, 17, ...
```

This distributes work evenly across agents. Each agent receives roughly the same number of items regardless of total count.

## Agent Launch Pattern

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",           # or "sonnet" for complex analysis
  run_in_background: true,
  description: "Process batch N",
  prompt: |
    Process these items: [batch items]
    Write results to: .erk/scratch/<run-id>/batch-<N>.md
    Final message MUST be: "Output written to <path>"
)
```

Key constraints:

- **`run_in_background: true`** — allows parallel execution
- **Explicit output path** — agents must know where to write
- **Final message convention** — signals completion without ambiguity

## Verification Before Reading

After `TaskOutput` confirms completion, verify files before reading:

```bash
ls -la .erk/scratch/<run-id>/
```

This catches agent failures that produced no output. Missing files indicate an agent that crashed or failed silently.

## Current Implementations

| Command      | Agents | Model  | Purpose                        |
| ------------ | ------ | ------ | ------------------------------ |
| `audit-scan` | 5      | haiku  | Score docs for audit priority  |
| `learn`      | 4      | sonnet | Session + diff + docs analysis |

## Related Documentation

- [Token Optimization Patterns](token-optimization-patterns.md) — Task agent delegation for cost efficiency
