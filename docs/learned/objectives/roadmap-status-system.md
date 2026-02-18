---
title: Roadmap Status System
read_when:
  - "understanding how objective roadmap status is determined"
  - "working with roadmap step status values"
  - "debugging unexpected status in an objective roadmap"
tripwires:
  - action: "inferring status from PR column when explicit status is set"
    warning: "Explicit status values (done, in_progress, pending, blocked, skipped, planning) always take priority over PR-based inference. Only '-' or empty values trigger PR-based inference."
  - action: "treating status as a single-source value"
    warning: "Status resolution uses a two-tier system: explicit values first, then PR-based inference. Always check both the Status and PR columns."
  - action: "expecting status to auto-update when PR column is edited manually"
    warning: "Only the update-objective-node command writes computed status. Manual PR edits leave status unchanged — set status to '-' to re-enable inference."
last_audited: "2026-02-17 16:00 PT"
audit_result: edited
---

# Roadmap Status System

Objective roadmap tables use a **two-tier status resolution system** where explicit status values take absolute priority, and PR-based inference only activates as a fallback. This design exists because roadmap tables serve two audiences simultaneously: the parser (which needs deterministic status) and humans reading raw markdown on GitHub (who need the table to make sense without running code).

## Why Two Tiers?

The obvious design would be single-source: either always use the Status column or always infer from PR. Neither works alone:

- **Status-only** forces every workflow step (plan-save, PR landing, manual updates) to explicitly write status — easy to forget, leading to stale values
- **PR-inference-only** can't represent `blocked` or `skipped` states, since those have no PR column equivalent

The two-tier design lets normal workflow rely on PR inference (Tier 2) while reserving explicit status (Tier 1) for edge cases that PR state can't express.

## Tier 1: Explicit Status Values

When the Status column contains a recognized value, it takes absolute priority regardless of the PR column. The recognized values are: `done`, `in_progress`, `pending`, `planning`, `blocked`, `skipped`.

The parser expects `in_progress` (underscore) in the YAML frontmatter. The `update-objective-node` command writes `in-progress` (hyphenated) for display in markdown tables, but the frontmatter uses `in_progress` consistently.

### The "planning" Status

The `planning` status indicates a step has been dispatched for autonomous planning and implementation (via `erk objective plan`). It is set when a draft PR is created from an objective step, before the work transitions to `in_progress`. The transition path is: `pending` → `planning` (draft PR created) → `in_progress` (work begins) → `done` (PR landed). The `planning` status is treated as a non-terminal active state by the check command — steps with `planning` status are not flagged for PR/status consistency issues (see `check_cmd.py:137,147`).

## Tier 2: PR-Based Inference

When the Status column is `-` or empty (or any unrecognized value), the parser falls through to infer status from the PR column:

| Plan Column  | PR Column    | Inferred Status | Reasoning                                                                    |
| ------------ | ------------ | --------------- | ---------------------------------------------------------------------------- |
| any          | `#123`       | in_progress     | A PR reference means work is in flight (use --status done to confirm merged) |
| `#456`       | `-` or empty | in_progress     | A plan issue means work is underway                                          |
| `-` or empty | `-` or empty | pending         | No references means work hasn't started                                      |

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, parse_roadmap -->

See the status resolution logic in `parse_roadmap()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`.

## Resolution Examples

| Status Column | PR Column  | Final Status | Why                                             |
| ------------- | ---------- | ------------ | ----------------------------------------------- |
| `done`        | `-`        | done         | Explicit — no inference needed                  |
| `-`           | `#123`     | in_progress  | Tier 2 inference from PR (not confirmed merged) |
| `blocked`     | `#123`     | blocked      | Explicit overrides PR (step blocked despite PR) |
| `-`           | `plan #45` | in_progress  | Tier 2 inference from plan reference            |
| `pending`     | `#123`     | pending      | Explicit overrides PR (intentional hold)        |
| `-`           | `-`        | pending      | Both empty — default                            |

## The Write/Read Asymmetry

The most important cross-cutting insight: **mutation writes both cells, but parsing only infers from one**. This asymmetry is intentional.

<!-- Source: src/erk/cli/commands/exec/scripts/update_objective_node.py, _replace_node_refs_in_body -->

The `update-objective-node` command computes display status from the plan/PR values and writes both the Status and PR cells atomically. PR reference alone infers `in_progress` (not `done`); callers that know the PR is merged must pass `--status done` explicitly. This prevents premature "done" status when a PR exists but hasn't been confirmed as merged. But `parse_roadmap()` only falls through to PR inference when the Status cell is `-` or empty.

This creates a subtle trap: if you update the PR cell **without using the command** (e.g., manual GitHub edit or direct body mutation), the Status cell retains its old value and the parser will respect that stale explicit value. To re-enable inference after manual edits, set the Status cell to `-`.

## Validation Catches Inconsistencies

<!-- Source: src/erk/cli/commands/objective/check_cmd.py, validate_objective -->

The `erk objective check` command validates status/PR consistency after parsing. It flags cases where explicit status contradicts the PR column — for example, a step with PR `#123` but status `pending`. Steps with a PR are expected to be `in_progress` (PR open) or `done` (PR merged); other statuses like `pending` usually indicate a forgotten status update rather than an intentional override.

## Inference Rules vs Validity Constraints

Status inference (Tier 2) determines what status _should be_ from PR/plan columns. Validity constraints (check command) determine what combinations are _allowed_. These are distinct:

- **Inference**: "Status is `-`, PR is `#123` → infer `in_progress`"
- **Validity**: "Status is `done` with `plan: #456` → flag as potentially inconsistent"

### Valid Plan Reference States

A node with a plan reference (`plan: #NNN`) can validly be in these statuses:

- `in_progress` — actively being worked on
- `done` — PR has landed (this is the expected end state after `objective-update-with-landed-pr`)
- `planning` — dispatched for autonomous planning
- `skipped` — explicitly marked as no longer needed

A `done` node with a plan reference is normal — it means the plan produced a PR that has since landed.

## When to Use Each Tier

| Situation                             | Approach                                | Why                                             |
| ------------------------------------- | --------------------------------------- | ----------------------------------------------- |
| Normal workflow (plan-save, PR lands) | Use `update-objective-node`             | Writes both cells atomically, always consistent |
| Step blocked by external dependency   | Set Status to `blocked` manually        | No PR column value can express "blocked"        |
| Step no longer needed                 | Set Status to `skipped` manually        | No PR column value can express "skipped"        |
| Intentional hold despite existing PR  | Set Status to `pending` manually        | Overrides the PR inference deliberately         |
| Quick fix via GitHub UI               | Update both cells, or set Status to `-` | Avoids the stale-status trap                    |

## Related Documentation

- [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) — Details on the write-side behavior and the command vs direct mutation decision
- [Roadmap Parser](roadmap-parser.md) — Full parsing rules, table format, and validation
