---
title: Branch Naming Conventions
read_when:
  - "creating or modifying branch name generation"
  - "extracting issue or objective numbers from branch names"
  - "working with generate_issue_branch_name(), generate_draft_pr_branch_name(), or extract functions"
tripwires:
  - action: "constructing branch names manually"
    warning: "Use generate_issue_branch_name() for consistent objective ID encoding."
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
---

# Branch Naming Conventions

All erk-managed branches follow a canonical naming pattern that encodes plan and objective references for downstream inference.

## Canonical Function

<!-- Source: packages/erk-shared/src/erk_shared/naming.py, generate_issue_branch_name -->

See `generate_issue_branch_name()` in `packages/erk-shared/src/erk_shared/naming.py`. Accepts `issue_number`, `title`, `timestamp`, and optional `objective_id` keyword argument.

## Branch Format

### Issue-Based Branches

**Without objective:**

```
P{issue}-{slug}-{MM-DD-HHMM}
```

**With objective:**

```
P{issue}-O{objective}-{slug}-{MM-DD-HHMM}
```

**Examples:**

- `P123-fix-auth-bug-01-15-1430`
- `P123-O456-fix-auth-bug-01-15-1430`

### Draft-PR Branches

**Without objective:**

```
plan/{slug}-{MM-DD-HHMM}
```

**With objective:**

```
plan/O{objective}-{slug}-{MM-DD-HHMM}
```

**Examples:**

- `plan/fix-auth-bug-01-15-1430`
- `plan/O456-fix-auth-bug-01-15-1430`

Draft-PR branches have no extractable plan ID from the branch name. `plan-ref.json` is the sole source of truth.

**Constraints:**

- Prefix (`P{num}-` or `P{num}-O{obj}-` or `plan/`) + sanitized title must not exceed 31 characters
- Title is sanitized via `sanitize_worktree_name()` (lowercased, special chars replaced with hyphens)
- Timestamp suffix: `-MM-DD-HHMM` format
- Trailing hyphens stripped before timestamp

## Extraction Functions

### extract_leading_issue_number()

<!-- Source: packages/erk-shared/src/erk_shared/naming.py, extract_leading_issue_number -->

Extracts the plan issue number from a branch name. See `extract_leading_issue_number()` in `packages/erk-shared/src/erk_shared/naming.py`.

- `"P2382-convert-erk-create-12-05-2359"` -> `2382`
- `"P123-O456-fix-auth-bug-01-15-1430"` -> `123`
- Supports legacy format without `P` prefix for backwards compatibility

### extract_objective_number()

<!-- Source: packages/erk-shared/src/erk_shared/naming.py, extract_objective_number -->

Extracts the optional objective ID from a branch name. Supports both issue-based (`P{issue}-O{obj}-`) and draft-PR (`plan/O{obj}-`) patterns. See `extract_objective_number()` in `packages/erk-shared/src/erk_shared/naming.py`.

- `"P123-O456-fix-auth-bug-01-15-1430"` -> `456`
- `"plan/O456-fix-auth-01-15-1430"` -> `456`
- `"P123-fix-auth-bug-01-15-1430"` -> `None`
- `"plan/fix-auth-bug-01-15-1430"` -> `None`
- Case-insensitive: `"P123-o456-fix-bug"` -> `456`

## Usage Sites

Branch creation codepaths delegate to one of two functions depending on whether a plan issue exists:

**`generate_issue_branch_name()`** — for issue-backed plans (`P{issue}-...`):

| Codepath              | File                                        |
| --------------------- | ------------------------------------------- |
| Plan submit           | `src/erk/cli/commands/submit.py`            |
| One-shot dispatch     | `src/erk/cli/commands/one_shot_dispatch.py` |
| setup-impl-from-issue | Branch creation during implementation       |

**`generate_draft_pr_branch_name()`** — for draft-PR plans (`plan/...`):

| Codepath                 | File                                                            |
| ------------------------ | --------------------------------------------------------------- |
| Plan save (draft-PR)     | `src/erk/cli/commands/exec/scripts/plan_save.py`                |
| Plan migrate to draft-PR | `src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py` |

The one-shot dispatch also has a fallback for non-plan tasks: `oneshot-{slug}-{MM-DD-HHMM}`.

## Related Topics

- [Branch Name Inference](../planning/branch-name-inference.md) - How plan/PR recovery uses the P{issue} prefix contract
