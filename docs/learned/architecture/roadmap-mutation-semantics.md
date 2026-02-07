---
title: Roadmap Mutation Semantics
last_audited: "2026-02-07 18:35 PT"
audit_result: edited
read_when:
  - "modifying objective roadmap update logic"
  - "understanding status inference when updating roadmap steps"
  - "working with update-roadmap-step command"
tripwires:
  - action: "updating a roadmap step's PR cell"
    warning: "The update-roadmap-step command computes the display status from the PR value (e.g., '#123' → 'done', 'plan #123' → 'in-progress', empty → 'pending') and writes it directly into the status cell. It does NOT reset status to '-'."
  - action: "inferring status from PR column when status is explicitly set"
    warning: "Explicit status values (done, in-progress, pending, blocked, skipped) always override PR-based inference in parse_roadmap(). Only '-' or empty allows inference."
---

# Roadmap Mutation Semantics

The `update-roadmap-step` command updates PR cells in objective roadmap tables with computed status values. Understanding the interaction between the Status and PR columns is essential for correct roadmap mutations.

## Two-Tier Status Resolution (Parser)

The roadmap parser (`parse_roadmap()` in `objective_roadmap_shared.py`, lines 102-115) uses a two-tier system to determine step status:

**Tier 1: Explicit Status Values (highest priority)**

When the Status column contains explicit values, they override PR-based inference:

| Status Column Value            | Result Status | Notes                                   |
| ------------------------------ | ------------- | --------------------------------------- |
| `done`                         | `done`        | Explicit override                       |
| `in-progress` or `in_progress` | `in_progress` | Explicit override (both forms accepted) |
| `pending`                      | `pending`     | Explicit override                       |
| `blocked`                      | `blocked`     | Explicit override                       |
| `skipped`                      | `skipped`     | Explicit override                       |

**Tier 2: PR-Based Inference (for `-` or empty values)**

When the Status column is `-` or empty, status is inferred from the PR column:

| PR Column Value | Inferred Status |
| --------------- | --------------- |
| `#123`          | `done`          |
| `plan #456`     | `in_progress`   |
| `-` or empty    | `pending`       |

> **Source**: See [`objective_roadmap_shared.py:102-115`](../../../src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py)

## update-roadmap-step Command

**Purpose:** Atomically update a step's PR cell with computed status.

**Usage:**

```bash
erk exec update-roadmap-step 6423 --step 1.3 --pr "plan #6464"
erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500"
erk exec update-roadmap-step 6423 --step 1.3 --pr ""
```

**Behavior:** When the command updates a step's PR cell, it also computes and writes the display status directly into the status cell based on the PR value:

| PR Value     | Written Status | Written PR Cell |
| ------------ | -------------- | --------------- |
| `#123`       | `done`         | `#123`          |
| `plan #456`  | `in-progress`  | `plan #456`     |
| empty string | `pending`      | `-`             |

This means the status cell always reflects the current state. The parser's Tier 2 inference is relevant when reading roadmaps that were edited manually (where status might be `-`), but the CLI command writes explicit status values.

**Capabilities:**

- Updates the PR cell for a specific step
- Computes display status from PR value and writes it into the status cell
- Simpler mental model: "set step X's PR to Y"
- Designed for plan-save workflow integration

## LBYL Pattern in Update Command

The update command uses LBYL throughout:

```python
# Check result type before accessing fields
if isinstance(issue, IssueNotFound):
    # Handle missing issue

# Check parse result before using
if not phases:
    # Handle empty roadmap
```

## PR Cell Mutation Pattern

The command uses a regex pattern for row matching and cell replacement:

```python
# Match table row: | step_id | description | status | pr |
pattern = re.compile(
    r"^\|(\s*" + re.escape(step_id) + r"\s*)\|(.+?)\|(.+?)\|(.+?)\|$",
    re.MULTILINE,
)
```

All four cells are captured. The step_id and description cells are preserved; the status and PR cells are replaced.

## Reference Implementation

- Step mutation: `src/erk/cli/commands/exec/scripts/update_roadmap_step.py:63-97`
- Two-tier status resolution: `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py:102-115`

## Related Documentation

- [Update Roadmap Step Command](../cli/commands/update-roadmap-step.md) — Step-level PR updates
- [Roadmap Parser](../objectives/roadmap-parser.md) — Parsing rules and CLI usage
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — The isinstance() checking pattern
