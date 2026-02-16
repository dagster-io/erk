---
title: Roadmap Mutation Semantics
last_audited: "2026-02-08 00:30 PT"
audit_result: edited
read_when:
  - "modifying objective roadmap update logic"
  - "understanding status inference when updating roadmap steps"
  - "working with update-roadmap-step command"
tripwires:
  - action: "updating a roadmap step's PR cell"
    warning: "The update-roadmap-step command computes display status from the PR value and writes it directly into the status cell. Status inference only happens during parsing when status is '-' or empty."
  - action: "expecting status to auto-update after manual PR edits"
    warning: "Only the update-roadmap-step command writes computed status. Manual GitHub edits or direct body mutations leave status at its current value — you must explicitly set status to '-' to enable inference on next parse."
  - action: "implementing functions that update roadmap data in frontmatter, body table, or comment table"
    warning: "Audit ALL write paths for semantic consistency. Auto-clear/auto-infer/auto-compute logic must be replicated across all locations. The frontmatter and table updaters must implement identical semantics for operations like auto-clearing plan when PR is set."
---

# Roadmap Mutation Semantics

This document explains how status values interact with PR column updates when mutating objective roadmap tables. Understanding the distinction between **mutation-time computation** (command writes status) and **parse-time inference** (parser reads status) is critical for correct roadmap updates.

## The Key Distinction: Write vs Read

Roadmap status resolution happens in **two different contexts** with different semantics:

1. **Mutation context** (`update-roadmap-step` command): Computes status from PR value and **writes both cells atomically**
2. **Parse context** (`parse_roadmap()` function): Reads status cell and **infers only if status is `-` or empty**

This split means the command produces human-readable tables (status always reflects PR state), while the parser handles legacy or manually-edited tables (where status might be stale or explicit).

## Mutation: The update-roadmap-step Command

### What It Does

When you run `erk exec update-roadmap-step 6423 --step 1.3 --plan "#6464"`, the command:

1. Computes display status from the plan/PR values
2. Writes **status, plan, and PR cells** in a single atomic update

| Flag Provided   | Written Status | Written Plan Cell | Written PR Cell |
| --------------- | -------------- | ----------------- | --------------- |
| `--pr "#123"`   | `done`         | `-`               | `#123`          |
| `--plan "#456"` | `in-progress`  | `#456`            | `-`             |
| `--pr ""`       | `pending`      | `-`               | `-`             |

### Why Both Cells Are Written

The command could have written PR and left status as `-` (relying on parse-time inference), but that creates a worse user experience:

- **GitHub viewers** see the raw markdown table — status would show `-` until the next parse
- **Manual edits** would require understanding the inference rules
- **Audit trail** becomes unclear (did someone forget to update status, or is inference intended?)

By writing computed status directly, the table is always human-readable.

### Implementation Detail

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, _replace_step_refs_in_body -->

See `_replace_step_refs_in_body()` in `src/erk/cli/commands/exec/scripts/update_roadmap_step.py`. The function uses regex to find the target row and replaces status, plan, and PR cells in a single operation. It supports both 4-col (legacy) and 5-col table formats, upgrading 4-col headers to 5-col on write.

## Parse: Status Inference at Read Time

The parser (`parse_roadmap()`) uses a two-tier status resolution system: explicit status values take priority, with PR-based inference only when status is `-` or empty. For the complete specification, see [Roadmap Status System](../objectives/roadmap-status-system.md).

The key point for mutation semantics: inference only fires when the status cell is `-` or empty. If a cell already has an explicit value (even a stale one), the parser preserves it.

### Why This Matters for Mutations

If you update PR via direct body mutation (not using the command), status won't auto-update:

| Action                                            | Result Status | Why                                                  |
| ------------------------------------------------- | ------------- | ---------------------------------------------------- |
| update-roadmap-step `--pr "#123"`                 | `done`        | Command writes computed status                       |
| update-roadmap-step `--plan "#456"`               | `in-progress` | Command writes computed status                       |
| Manual GitHub edit: change PR cell to `#123`      | (unchanged)   | Status cell not touched, parser reads explicit value |
| Script sets PR but leaves status at `in-progress` | `in_progress` | Parser sees explicit value, doesn't infer            |

To enable inference after manual/script edits, you must explicitly set status to `-`.

## Decision Table: Command vs Direct Mutation

| Context                                   | Use Command                     | Direct Body Mutation                           |
| ----------------------------------------- | ------------------------------- | ---------------------------------------------- |
| Normal workflow (plan-save, PR landing)   | ✅ Atomic PR + status update    | ❌ Would leave status stale                    |
| Batch updates across multiple steps       | ✅ One call per step            | ⚠️ Possible, but must compute status           |
| Setting explicit status (blocked/skipped) | ❌ Command doesn't support this | ✅ Write status column directly                |
| Quick fix in GitHub UI                    | N/A                             | ⚠️ Must update both cells or set status to `-` |

The command is designed for **normal workflow integration** (skills, hooks, scripts). For special cases like marking steps as `blocked`, direct body mutation is still required.

## LBYL Pattern in Update Command

The command follows erk's LBYL discipline throughout, using discriminated union checks before each operation. See the `update_roadmap_step()` function in `src/erk/cli/commands/exec/scripts/update_roadmap_step.py:107-182` for the full pattern. For the general approach, see [Discriminated Union Error Handling](discriminated-union-error-handling.md).

## Dual-Write Consistency Pattern

A single logical operation (e.g., "set PR reference for step 1.2") may touch multiple data stores:

- YAML frontmatter in issue body
- Markdown table in issue body (v1 format)
- Markdown table in comment body (v2 format)

If one updater implements auto-clear logic (e.g., "clear plan when PR is set") but others preserve existing values, the stores diverge. This has caused bugs twice: status auto-inference divergence and plan auto-clear divergence (PR #7151).

### Audit Checklist

Before merging any PR that modifies roadmap update logic:

1. Identify all functions that write to the same logical data
2. Verify each function handles the same edge cases identically
3. Write integration tests that verify all stores produce identical output for the same operation

### Source

See `update_step_in_frontmatter()` in `erk_shared/gateway/github/metadata/roadmap.py` and `_replace_table_in_text()` / `_replace_step_refs_in_body()` in `src/erk/cli/commands/exec/scripts/update_roadmap_step.py` for the canonical implementation of auto-clear semantics.

## Cross-Document Knowledge

This document explains **mutation semantics** (what changes when you update PR). For related concerns:

- **Parsing rules and validation** → [Roadmap Parser](../objectives/roadmap-parser.md)
- **Two-tier status resolution details** → [Roadmap Status System](../objectives/roadmap-status-system.md)
- **Command usage and exit codes** → [Update Roadmap Step Command](../cli/commands/update-roadmap-step.md)
- **Batch vs surgical update decisions** → [Roadmap Mutation Patterns](../objectives/roadmap-mutation-patterns.md)

The key insight unique to this document: **mutation writes both cells, parsing infers from one**. This asymmetry is intentional and solves the human-readability vs backward-compatibility trade-off.
