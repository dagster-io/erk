---
title: Roadmap Mutation Semantics
last_audited: "2026-02-17 12:00 PT"
audit_result: clean
read_when:
  - "modifying objective roadmap update logic"
  - "understanding status inference when updating roadmap steps"
  - "working with update-roadmap-step command"
tripwires:
  - action: "updating a roadmap step's PR cell"
    warning: "The update-roadmap-step command computes display status from the PR value and writes it directly into the status cell. Status inference only happens during parsing when status is '-' or empty."
  - action: "expecting status to auto-update after manual PR edits"
    warning: "Only the update-roadmap-step command writes computed status. Manual GitHub edits or direct body mutations leave status at its current value — you must explicitly set status to '-' to enable inference on next parse."
  - action: "setting PR reference without providing --plan"
    warning: "The CLI requires --plan when --pr is set (error: plan_required_with_pr). Use --plan '#NNN' to preserve or --plan '' to explicitly clear. Read roadmap-mutation-semantics.md for the None/empty/value semantics."
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

| Flag Provided                             | Written Status | Written Plan Cell | Written PR Cell |
| ----------------------------------------- | -------------- | ----------------- | --------------- |
| `--pr "#123" --plan "#456"`               | `in-progress`  | `#456`            | `#123`          |
| `--pr "#123" --plan "#456" --status done` | `done`         | `#456`            | `#123`          |
| `--plan "#456"`                           | `in-progress`  | `#456`            | `-`             |
| `--pr "" --plan ""`                       | `pending`      | `-`               | `-`             |

### None vs Empty-String vs Value Semantics

The `update_step_in_frontmatter()` function uses a three-way convention for its `plan` and `pr` parameters:

| Value    | Meaning                             |
| -------- | ----------------------------------- |
| `None`   | Preserve existing value (no change) |
| `""`     | Clear the field (set to `None`)     |
| `"#123"` | Set to the specified value          |

This allows callers to update one field without affecting the other. For example, `--plan "#456"` without `--pr` preserves the existing PR value.

### --plan Is Required When --pr Is Set

When `--pr` is explicitly set (non-None, non-empty), `--plan` **must** also be provided. The CLI rejects `--pr` without `--plan` with error `plan_required_with_pr` to prevent accidental loss of the plan reference. The caller must explicitly choose to preserve (`--plan "#NNN"`) or clear (`--plan ""`) the plan field.

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, lines 354-366 -->

| Flags Provided              | Plan Result | PR Result | Notes                      |
| --------------------------- | ----------- | --------- | -------------------------- |
| `--pr "#123"`               | **Error**   | —         | `plan_required_with_pr`    |
| `--pr "#123" --plan "#456"` | `"#456"`    | `"#123"`  | Explicit plan preserved    |
| `--pr "#123" --plan ""`     | Cleared     | `"#123"`  | Explicit clear             |
| `--plan "#456"`             | `"#456"`    | Preserved | PR not provided, preserved |
| `--pr "" --plan ""`         | Cleared     | Cleared   | Both explicitly cleared    |

### Why Both Cells Are Written

The command could have written PR and left status as `-` (relying on parse-time inference), but that creates a worse user experience:

- **GitHub viewers** see the raw markdown table — status would show `-` until the next parse
- **Manual edits** would require understanding the inference rules
- **Audit trail** becomes unclear (did someone forget to update status, or is inference intended?)

By writing computed status directly, the table is always human-readable.

### Implementation Detail

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, _replace_step_refs_in_body -->

The update command uses two functions in `src/erk/cli/commands/exec/scripts/update_roadmap_step.py`: `_replace_step_refs_in_body()` updates the YAML frontmatter (source of truth), while `_replace_table_in_text()` updates the rendered 5-column markdown table in the objective-body comment.

### Status Inference Is Write-Time Only

Status is computed by `update_step_in_frontmatter()` at mutation time. There is no read-time inference in the v2 YAML path — `parse_roadmap()` reads the `status` field directly from YAML. The inference logic (explicit > infer from PR/plan > preserve) runs only during writes:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, update_step_in_frontmatter lines 322-331 -->

1. **Explicit status provided** → use it directly
2. **PR is set** → status = `"in_progress"`
3. **Plan is set** → status = `"in_progress"`
4. **Neither** → preserve existing status

## Parse: Status Inference at Read Time (Legacy Tables Only)

The parser (`parse_roadmap()`) uses a two-tier status resolution system: explicit status values take priority, with PR-based inference only when status is `-` or empty. For the complete specification, see [Roadmap Status System](../objectives/roadmap-status-system.md).

The key point for mutation semantics: inference only fires when the status cell is `-` or empty. If a cell already has an explicit value (even a stale one), the parser preserves it.

### Why This Matters for Mutations

If you update PR via direct body mutation (not using the command), status won't auto-update:

| Action                                            | Result Status | Why                                                                  |
| ------------------------------------------------- | ------------- | -------------------------------------------------------------------- |
| update-roadmap-step `--plan "#456" --pr "#123"`   | `in-progress` | Command writes computed status (PR ≠ done without explicit --status) |
| update-roadmap-step `--plan "#456"`               | `in-progress` | Command writes computed status                                       |
| Manual GitHub edit: change PR cell to `#123`      | (unchanged)   | Status cell not touched, parser reads explicit value                 |
| Script sets PR but leaves status at `in-progress` | `in_progress` | Parser sees explicit value, doesn't infer                            |

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
