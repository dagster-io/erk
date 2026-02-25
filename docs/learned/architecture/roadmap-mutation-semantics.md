---
title: Roadmap Mutation Semantics
last_audited: "2026-02-25 18:00 PT"
audit_result: edited
read_when:
  - "modifying objective roadmap update logic"
  - "understanding status inference when updating roadmap steps"
  - "working with update-objective-node command"
tripwires:
  - action: "updating a roadmap step's PR cell"
    warning: "The update-objective-node command computes display status from the PR value and writes it directly into the status cell. Status inference only happens during parsing when status is '-' or empty."
  - action: "expecting status to auto-update after manual PR edits"
    warning: "Only the update-objective-node command writes computed status. Manual GitHub edits or direct body mutations leave status at its current value — you must explicitly set status to '-' to enable inference on next parse."
---

# Roadmap Mutation Semantics

This document explains how status values interact with PR column updates when mutating objective roadmap tables. Understanding the distinction between **mutation-time computation** (command writes status) and **parse-time inference** (parser reads status) is critical for correct roadmap updates.

## The Key Distinction: Write vs Read

Roadmap status resolution happens in **two different contexts** with different semantics:

1. **Mutation context** (`update-objective-node` command): Computes status from PR value and **writes both cells atomically**
2. **Parse context** (`parse_roadmap()` function): Reads status cell and **infers only if status is `-` or empty**

This split means the command produces human-readable tables (status always reflects PR state), while the parser handles legacy or manually-edited tables (where status might be stale or explicit).

## Mutation: The update-objective-node Command

### What It Does

When you run `erk exec update-objective-node 6423 --node 1.3 --pr "#123"`, the command:

1. Computes display status from the PR value
2. Writes **status and PR** in the YAML frontmatter atomically
3. Re-renders the comment table from the updated YAML

| Flag Provided                      | Written Status | Written PR Cell |
| ---------------------------------- | -------------- | --------------- |
| `--pr "#123"`                      | `in-progress`  | `#123`          |
| `--pr "#123" --status done`        | `done`         | `#123`          |
| `--pr "#123" --status in_progress` | `in-progress`  | `#123`          |
| `--pr ""`                          | `(preserved)`  | `(cleared)`     |

### None vs Empty-String vs Value Semantics

The `update_node_in_frontmatter()` function uses a three-way convention for its `pr` parameter:

| Value    | Meaning                             |
| -------- | ----------------------------------- |
| `None`   | Preserve existing value (no change) |
| `""`     | Clear the field (set to `None`)     |
| `"#123"` | Set to the specified value          |

This allows callers to update status without affecting the PR value.

### Why Both Cells Are Written

The command could have written PR and left status as `-` (relying on parse-time inference), but that creates a worse user experience:

- **GitHub viewers** see the raw markdown table — status would show `-` until the next parse
- **Manual edits** would require understanding the inference rules
- **Audit trail** becomes unclear (did someone forget to update status, or is inference intended?)

By writing computed status directly, the table is always human-readable.

### Implementation Detail

<!-- Source: src/erk/cli/commands/exec/scripts/update_objective_node.py -->

The update command updates the YAML frontmatter (source of truth), then re-renders the comment table via `rerender_comment_roadmap()`.

### Status Inference Is Write-Time Only

Status is computed by `update_node_in_frontmatter()` at mutation time. There is no read-time inference in the v2 YAML path — `parse_roadmap()` reads the `status` field directly from YAML. The inference logic runs only during writes:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, update_node_in_frontmatter -->

1. **Explicit status provided** → use it directly
2. **PR is set** → status = `"in_progress"`
3. **Neither** → preserve existing status

## Parse: Status Inference at Read Time (Legacy Tables Only)

The parser (`parse_roadmap()`) uses a two-tier status resolution system: explicit status values take priority, with PR-based inference only when status is `-` or empty. For the complete specification, see [Roadmap Status System](../objectives/roadmap-status-system.md).

The key point for mutation semantics: inference only fires when the status cell is `-` or empty. If a cell already has an explicit value (even a stale one), the parser preserves it.

### Why This Matters for Mutations

If you update PR via direct body mutation (not using the command), status won't auto-update:

| Action                                                   | Result Status | Why                                                  |
| -------------------------------------------------------- | ------------- | ---------------------------------------------------- |
| update-objective-node `--pr "#123"`                      | `in_progress` | Command writes computed status                       |
| update-objective-node `--pr "#123" --status done`        | `done`        | Explicit `--status done` confirms PR is merged       |
| update-objective-node `--pr "#123" --status in_progress` | `in-progress` | Explicit status overrides PR-based inference         |
| Manual GitHub edit: change PR cell to `#123`             | (unchanged)   | Status cell not touched, parser reads explicit value |
| Script sets PR but leaves status at `in-progress`        | `in_progress` | Parser sees explicit value, doesn't infer            |

To enable inference after manual/script edits, you must explicitly set status to `-`.

## Decision Table: Command vs Direct Mutation

| Context                                   | Use Command                    | Direct Body Mutation                        |
| ----------------------------------------- | ------------------------------ | ------------------------------------------- |
| Normal workflow (plan-save, PR landing)   | Yes: Atomic PR + status update | No: Would leave status stale                |
| Batch updates across multiple steps       | Yes: One call per step         | Possible, but must compute status           |
| Setting explicit status (blocked/skipped) | Yes: --status flag supports it | Also works: Write status column directly    |
| Quick fix in GitHub UI                    | N/A                            | Must update both cells or set status to `-` |

The command is designed for **normal workflow integration** (skills, hooks, scripts).

## LBYL Pattern in Update Command

The command follows erk's LBYL discipline throughout, using discriminated union checks before each operation. See the `update_objective_node()` function in `src/erk/cli/commands/exec/scripts/update_objective_node.py` for the full pattern. For the general approach, see [Discriminated Union Error Handling](discriminated-union-error-handling.md).

## Cross-Document Knowledge

This document explains **mutation semantics** (what changes when you update PR). For related concerns:

- **Parsing rules and validation** → [Roadmap Parser](../objectives/roadmap-parser.md)
- **Two-tier status resolution details** → [Roadmap Status System](../objectives/roadmap-status-system.md)
- **Command usage and exit codes** → [Update Roadmap Step Command](../cli/commands/update-objective-node.md)
- **Batch vs surgical update decisions** → [Roadmap Mutation Patterns](../objectives/roadmap-mutation-patterns.md)

The key insight unique to this document: **mutation writes both cells, parsing infers from one**. This asymmetry is intentional and solves the human-readability vs backward-compatibility trade-off.
