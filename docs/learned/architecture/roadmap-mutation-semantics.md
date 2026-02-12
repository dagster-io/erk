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
  - action: "implementing commands that update multiple GitHub entities"
    warning: "Use single-read, batch-update, single-write pattern. Fetch all needed data in one API call, apply N updates in memory, write once. Don't iterate with N API calls per update."
    score: 5
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

When you run `erk exec update-roadmap-step 6423 --step 1.3 --pr "plan #6464"`, the command:

1. Computes display status from the PR value
2. Writes **both** the status and PR cells in a single atomic update

| PR Value Provided | Written Status Cell | Written PR Cell |
| ----------------- | ------------------- | --------------- |
| `#123`            | `done`              | `#123`          |
| `plan #456`       | `in-progress`       | `plan #456`     |
| `""` (empty)      | `pending`           | `-`             |

### Why Both Cells Are Written

The command could have written PR and left status as `-` (relying on parse-time inference), but that creates a worse user experience:

- **GitHub viewers** see the raw markdown table — status would show `-` until the next parse
- **Manual edits** would require understanding the inference rules
- **Audit trail** becomes unclear (did someone forget to update status, or is inference intended?)

By writing computed status directly, the table is always human-readable.

### Implementation Detail

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, _replace_step_pr_in_body -->

See `_replace_step_pr_in_body()` in `src/erk/cli/commands/exec/scripts/update_roadmap_step.py:63-97`. The function uses regex to find the target row and replaces both status and PR cells in a single operation.

The computation logic (lines 84-90) maps PR values to status strings before building the replacement row.

## Parse: Status Inference at Read Time

The parser (`parse_roadmap()`) uses a two-tier status resolution system: explicit status values take priority, with PR-based inference only when status is `-` or empty. For the complete specification, see [Roadmap Status System](../objectives/roadmap-status-system.md).

The key point for mutation semantics: inference only fires when the status cell is `-` or empty. If a cell already has an explicit value (even a stale one), the parser preserves it.

### Why This Matters for Mutations

If you update PR via direct body mutation (not using the command), status won't auto-update:

| Action                                            | Result Status | Why                                                  |
| ------------------------------------------------- | ------------- | ---------------------------------------------------- |
| update-roadmap-step sets PR to `#123`             | `done`        | Command writes computed status                       |
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

## Cross-Document Knowledge

This document explains **mutation semantics** (what changes when you update PR). For related concerns:

- **Parsing rules and validation** → [Roadmap Parser](../objectives/roadmap-parser.md)
- **Two-tier status resolution details** → [Roadmap Status System](../objectives/roadmap-status-system.md)
- **Command usage and exit codes** → [Update Roadmap Step Command](../cli/commands/update-roadmap-step.md)
- **Batch vs surgical update decisions** → [Roadmap Mutation Patterns](../objectives/roadmap-mutation-patterns.md)

The key insight unique to this document: **mutation writes both cells, parsing infers from one**. This asymmetry is intentional and solves the human-readability vs backward-compatibility trade-off.
