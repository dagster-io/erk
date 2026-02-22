---
title: Backpressure Path Registry
read_when:
  - "adding a new validation gate or sanitization function"
  - "deciding whether a code path should gate (reject) or transform (sanitize) input"
  - "tracing which call sites use gates vs silent transformation"
  - "working with worktree names, plan titles, or tripwire candidates"
tripwires:
  - action: "adding a new sanitize/validate pair without updating this registry"
    warning: "New gate/transform domains must be documented here so agents know which paths are gated. See the 'Adding New Paths' section."
  - action: "calling sanitize_worktree_name() in agent-facing code without validate_worktree_name()"
    warning: "Agent-facing paths must gate (reject invalid input), not silently transform. Use validate_worktree_name() and return actionable feedback."
last_audited: "2026-02-22 21:35 PT"
---

# Backpressure Path Registry

Concrete cross-domain reference of which code paths use **gates** (reject invalid input with feedback) vs **transformation** (silently sanitize input). For the conceptual pattern, see [Agent Back Pressure via Gates](agent-backpressure-gates.md).

## Decision Rule

| Producer | Strategy                           | Rationale                               |
| -------- | ---------------------------------- | --------------------------------------- |
| Agent    | **Gate** (validate, reject, retry) | Agent can self-correct from feedback    |
| Human    | **Transform** (sanitize silently)  | UX matters more than compliance signals |

## Domain 1: Worktree Names

Core functions in `packages/erk-shared/src/erk_shared/naming.py`:

- **`validate_worktree_name()`** (line 257) — Gate. Returns `ValidWorktreeName | InvalidWorktreeName`. Checks whether `sanitize_worktree_name()` would change the input; rejects if it would.
- **`sanitize_worktree_name()`** (line 364) — Transform. Lowercases, replaces unsafe chars, collapses hyphens, truncates to 31 chars. Returns a clean string silently.

### Gate Sites (Agent-Facing)

| Call Site                     | File                                                             | What Happens                                                                         |
| ----------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `prepare_plan_for_worktree()` | `packages/erk-shared/src/erk_shared/issue_workflow.py:130`       | Sanitizes branch name, then validates. Returns `IssueValidationFailed` on rejection. |
| `setup_impl_from_issue.py`    | `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py:311` | Validates `sanitize_worktree_name(branch_name)`. Exits with error JSON on failure.   |

### Transform Sites (Human-Facing)

| Call Site                    | File                                                            | What Happens                                                                                                                                  |
| ---------------------------- | --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `wt create` (multiple paths) | `src/erk/cli/commands/wt/create_cmd.py:163,586,596,606,625,712` | Sanitizes branch/name to worktree name. Six call sites covering different input sources (current branch, from-branch, stem, explicit branch). |
| `wt rename`                  | `src/erk/cli/commands/wt/rename_cmd.py:35`                      | Sanitizes new name provided by user.                                                                                                          |
| `one_shot_dispatch.py`       | `src/erk/cli/commands/one_shot_dispatch.py:96`                  | Sanitizes title for branch name generation.                                                                                                   |
| `branch_slug_generator.py`   | `src/erk/core/branch_slug_generator.py:120`                     | Safety net sanitization on slug output.                                                                                                       |
| `stack/split`                | `src/erk/cli/commands/stack/split_old/plan.py:166`              | Sanitizes branch for worktree split.                                                                                                          |
| `implement_shared.py`        | `src/erk/cli/commands/implement_shared.py:603`                  | Sanitizes cleaned stem for worktree name.                                                                                                     |

### Internal Uses (Within naming.py)

| Call Site                         | Line            | What Happens                                           |
| --------------------------------- | --------------- | ------------------------------------------------------ |
| `validate_worktree_name()`        | `naming.py:279` | Calls `sanitize_worktree_name()` to check idempotency. |
| `generate_issue_branch_name()`    | `naming.py:872` | Sanitizes title component of branch name.              |
| `generate_draft_pr_branch_name()` | `naming.py:915` | Sanitizes title component of `plnd/` branch name.      |

## Domain 2: Plan Titles

Core functions in `packages/erk-shared/src/erk_shared/naming.py`:

- **`validate_plan_title()`** (line 128) — Gate. Returns `ValidPlanTitle | InvalidPlanTitle`. Checks length, alphabetic content, fallback titles, and whether `generate_filename_from_title()` retains meaningful content.
- **`generate_filename_from_title()`** (line 454) — Transform. Converts title to kebab-case `*-plan.md` filename. Strips emojis, normalizes unicode, returns `"plan.md"` fallback for empty results.

### Gate Sites (Agent-Facing)

| Call Site                    | File                                                              | What Happens                                                                            |
| ---------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `plan_save.py`               | `src/erk/cli/commands/exec/scripts/plan_save.py:145`              | Validates title in `_save_as_draft_pr()`. Outputs error JSON on failure.                |
| `plan_save_to_issue.py`      | `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py:190`     | Validates title before creating GitHub issue. Outputs error on failure.                 |
| `issue_title_to_filename.py` | `src/erk/cli/commands/exec/scripts/issue_title_to_filename.py:32` | Validates title, then generates filename at line 45. Exit code 2 on validation failure. |

### Transform Sites (Internal)

| Call Site                      | File                                                              | What Happens                                                                                                                                                        |
| ------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Inside `validate_plan_title()` | `naming.py:184`                                                   | Calls `generate_filename_from_title()` to check if meaningful content survives sanitization. Not a human-facing transform — used as a probe within the gate itself. |
| `issue_title_to_filename.py`   | `src/erk/cli/commands/exec/scripts/issue_title_to_filename.py:45` | Calls `generate_filename_from_title()` after gate passes. The gate ensures the title is valid; the transform produces the filename.                                 |

## Domain 3: Tripwire Candidates

Core functions in `packages/erk-shared/src/erk_shared/gateway/github/metadata/tripwire_candidates.py`:

- **`validate_candidates_data()`** (line 153) — Gate. Returns `ValidTripwireCandidates | InvalidTripwireCandidates`. Validates JSON structure: requires `candidates` list where each entry has `action`, `warning`, and `target_doc_path` strings.
- **`extract_tripwire_candidates_from_comments()`** (line 103) — Extraction (fail-open). Scans issue comments for tripwire-candidates metadata blocks. Returns empty list on any parse failure — **no gate, no rejection**.

Normalization function in `src/erk/cli/commands/exec/scripts/normalize_tripwire_candidates.py`:

- **`normalize_candidates_data()`** (line 63) — Transform. Normalizes agent-produced JSON (fixes structure, types). Returns `(normalized_dict, changed_bool)`.

### Gate Sites (Agent-Facing)

| Call Site                          | File                                                                     | What Happens                                                                                                                                             |
| ---------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `store_tripwire_candidates.py`     | `src/erk/cli/commands/exec/scripts/store_tripwire_candidates.py:85-86`   | Pipeline: `normalize_candidates_data()` then `validate_candidates_data()`. Normalize first to fix minor issues, then gate to reject structural problems. |
| `normalize_tripwire_candidates.py` | `src/erk/cli/commands/exec/scripts/normalize_tripwire_candidates.py:174` | Validates after normalization. Outputs error on failure.                                                                                                 |

### Extraction Sites (Fail-Open)

| Call Site                                     | File                         | What Happens                                                                                                                                              |
| --------------------------------------------- | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `extract_tripwire_candidates_from_comments()` | `tripwire_candidates.py:103` | Reads metadata from issue comments. Returns empty list on any failure — no gate, no rejection. Used for reading stored data, not validating agent output. |

## Core Function Reference

| Function                                      | File                                  | Role       | Returns                                                |
| --------------------------------------------- | ------------------------------------- | ---------- | ------------------------------------------------------ |
| `validate_worktree_name()`                    | `naming.py:257`                       | Gate       | `ValidWorktreeName \| InvalidWorktreeName`             |
| `sanitize_worktree_name()`                    | `naming.py:364`                       | Transform  | `str` (sanitized name)                                 |
| `validate_plan_title()`                       | `naming.py:128`                       | Gate       | `ValidPlanTitle \| InvalidPlanTitle`                   |
| `generate_filename_from_title()`              | `naming.py:454`                       | Transform  | `str` (filename)                                       |
| `validate_candidates_data()`                  | `tripwire_candidates.py:153`          | Gate       | `ValidTripwireCandidates \| InvalidTripwireCandidates` |
| `normalize_candidates_data()`                 | `normalize_tripwire_candidates.py:63` | Transform  | `tuple[dict, bool]`                                    |
| `extract_tripwire_candidates_from_comments()` | `tripwire_candidates.py:103`          | Extraction | `list[TripwireCandidate]`                              |

## Adding New Paths

When introducing a new validation/sanitization domain:

1. **Identify the producer**: Is the input coming from an agent or a human?
2. **Agent producer** → Create a `validate_*()` function that returns a discriminated union (`Valid* | Invalid*`). The invalid variant must include actionable feedback.
3. **Human producer** → Create a `sanitize_*()` or `transform_*()` function that silently produces valid output.
4. **If both producers exist** → Create both functions. Agent paths call the gate; human paths call the transform.
5. **Update this registry** with the new domain, function locations, and call sites.
