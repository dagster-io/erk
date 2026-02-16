---
title: Roadmap Status System
read_when:
  - "understanding how objective roadmap status is determined"
  - "working with roadmap step status values"
  - "debugging unexpected status in an objective roadmap"
tripwires:
  - action: "inferring status from PR column when explicit status is set"
    warning: "Explicit status values (done, in-progress, pending, blocked, skipped) always take priority over PR-based inference. Only '-' or empty values trigger PR-based inference."
  - action: "treating status as a single-source value"
    warning: "Status resolution uses a two-tier system: explicit values first, then PR-based inference. Always check both the Status and PR columns."
  - action: "expecting status to auto-update when PR column is edited manually"
    warning: "Only the update-roadmap-step command writes computed status. Manual PR edits leave status unchanged — set status to '-' to re-enable inference."
---

# Roadmap Status System

Objective roadmap tables use a **two-tier status resolution system** where explicit status values take absolute priority, and PR-based inference only activates as a fallback. This design exists because roadmap tables serve two audiences simultaneously: the parser (which needs deterministic status) and humans reading raw markdown on GitHub (who need the table to make sense without running code).

## Why Two Tiers?

The obvious design would be single-source: either always use the Status column or always infer from PR. Neither works alone:

- **Status-only** forces every workflow step (plan-save, PR landing, manual updates) to explicitly write status — easy to forget, leading to stale values
- **PR-inference-only** can't represent `blocked` or `skipped` states, since those have no PR column equivalent

The two-tier design lets normal workflow rely on PR inference (Tier 2) while reserving explicit status (Tier 1) for edge cases that PR state can't express.

## Tier 1: Explicit Status Values

When the Status column contains a recognized value, it takes absolute priority regardless of the PR column. The recognized values are: `done`, `in-progress`, `in_progress`, `pending`, `planning`, `blocked`, `skipped`.

Both `in-progress` (hyphenated, human-friendly in markdown) and `in_progress` (underscore, Python-friendly) are accepted and normalized to `in_progress` internally. This matters because the `update-roadmap-step` command writes `in-progress` for readability, but all downstream code uses `in_progress`.

### The "planning" Status

The `planning` status indicates a step has been dispatched for autonomous planning and implementation (via `erk objective next-plan`). It is set when a draft PR is created from an objective step, before the work transitions to `in_progress`. The transition path is: `pending` → `planning` (draft PR created) → `in_progress` (work begins) → `done` (PR landed). The `planning` status is treated as a non-terminal active state by the check command — steps with `planning` status are not flagged for PR/status consistency issues (see `check_cmd.py:137,147`).

## Tier 2: PR-Based Inference

When the Status column is `-` or empty (or any unrecognized value), the parser falls through to infer status from the PR column:

| Plan Column  | PR Column    | Inferred Status | Reasoning                               |
| ------------ | ------------ | --------------- | --------------------------------------- |
| any          | `#123`       | done            | A merged PR means work is complete      |
| `#456`       | `-` or empty | in_progress     | A plan issue means work is underway     |
| `-` or empty | `-` or empty | pending         | No references means work hasn't started |

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, parse_roadmap -->

See the status resolution logic in `parse_roadmap()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`.

## Resolution Examples

| Status Column | PR Column  | Final Status | Why                                             |
| ------------- | ---------- | ------------ | ----------------------------------------------- |
| `done`        | `-`        | done         | Explicit — no inference needed                  |
| `-`           | `#123`     | done         | Tier 2 inference from PR                        |
| `blocked`     | `#123`     | blocked      | Explicit overrides PR (step blocked despite PR) |
| `-`           | `plan #45` | in_progress  | Tier 2 inference from plan reference            |
| `pending`     | `#123`     | pending      | Explicit overrides PR (intentional hold)        |
| `-`           | `-`        | pending      | Both empty — default                            |

## The Write/Read Asymmetry

The most important cross-cutting insight: **mutation writes both cells, but parsing only infers from one**. This asymmetry is intentional.

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, _replace_step_refs_in_body -->

The `update-roadmap-step` command computes display status from the PR value and writes both the Status and PR cells atomically. It does this so the table is always human-readable on GitHub without requiring a parse pass. But `parse_roadmap()` only falls through to PR inference when the Status cell is `-` or empty.

This creates a subtle trap: if you update the PR cell **without using the command** (e.g., manual GitHub edit or direct body mutation), the Status cell retains its old value and the parser will respect that stale explicit value. To re-enable inference after manual edits, set the Status cell to `-`.

## Validation Catches Inconsistencies

<!-- Source: src/erk/cli/commands/objective/check_cmd.py, validate_objective -->

The `erk objective check` command validates status/PR consistency after parsing. It flags cases where explicit status contradicts the PR column — for example, a step with PR `#123` but status `in_progress`. These inconsistencies are valid (the explicit status wins by design), but the validator surfaces them as warnings because they usually indicate a forgotten status update rather than an intentional override.

## When to Use Each Tier

| Situation                             | Approach                                | Why                                             |
| ------------------------------------- | --------------------------------------- | ----------------------------------------------- |
| Normal workflow (plan-save, PR lands) | Use `update-roadmap-step`               | Writes both cells atomically, always consistent |
| Step blocked by external dependency   | Set Status to `blocked` manually        | No PR column value can express "blocked"        |
| Step no longer needed                 | Set Status to `skipped` manually        | No PR column value can express "skipped"        |
| Intentional hold despite existing PR  | Set Status to `pending` manually        | Overrides the PR inference deliberately         |
| Quick fix via GitHub UI               | Update both cells, or set Status to `-` | Avoids the stale-status trap                    |

## Related Documentation

- [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) — Details on the write-side behavior and the command vs direct mutation decision
- [Roadmap Parser](roadmap-parser.md) — Full parsing rules, table format, and validation
