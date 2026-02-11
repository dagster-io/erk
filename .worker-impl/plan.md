# Plan: Fix Objective Roadmap Status Display (Documentation & Validation)

> **Replans:** #6751

## What Changed Since Original Plan

PR #6552 (merged 2026-02-02, three days **before** this plan was created) implemented the core display status functionality:
- `update_roadmap_step.py` now computes and writes explicit display status (`done`/`in-progress`/`pending`)
- `objective_roadmap_shared.py` parser prioritizes explicit status values, falls back to PR-based inference for legacy `-`
- Test fixtures already updated to use correct display values

**Result:** ~80% of the original plan is already implemented. Only documentation fixes and an optional validation check remain.

## Investigation Findings

### Corrections to Original Plan

- **Change 1 (`display_status` field on `RoadmapStep`) is obsolete** — PR #6552 solved the problem differently by having the writer compute display status directly. No new dataclass field needed.
- **Change 5 (test fixture updates) already done** — PR #6552 updated all test fixtures.
- **Root cause is narrower:** Two stale documentation files still instruct agents to write `-` instead of explicit status values.

## Remaining Gaps

1. `objective-update-with-landed-pr.md` still instructs agents to set Status to `-` (lines 95, 99-104)
2. `plan-save.md` still describes `-` behavior (line 118)
3. No Check 6 exists in `check_cmd.py` to detect stale display statuses

## Implementation Steps

### Step 1: Update `objective-update-with-landed-pr.md`

**File:** `.claude/commands/erk/objective-update-with-landed-pr.md`

**Change A** — Line 95: Replace the instruction to set Status to `-`:
```
- Set the Status cell to `-` (inference determines status from PR column)
```
Replace with:
```
- Set the Status cell to the correct display value: `done` for completed steps (PR is `#NNN`), `in-progress` for in-flight plans (PR is `plan #NNN`), `pending` for no PR
```

**Change B** — Lines 99-104: Replace the stale "Status inference rules" block:
```
**Status inference rules:**

- Step has `#NNN` in PR column → Status `-` → inferred as `done`
- Step has `plan #NNN` in PR column → Status `-` → inferred as `in_progress`
- Step has no PR → Status stays as-is (inferred as `pending`)
- `blocked`/`skipped` in Status are explicit overrides — only change if blocker is resolved
```
Replace with:
```
**Status display rules:**

- Step has `#NNN` in PR column → Status `done`
- Step has `plan #NNN` in PR column → Status `in-progress`
- Step has no PR → Status `pending`
- `blocked`/`skipped` are explicit overrides — only change if blocker is resolved
```

### Step 2: Update `plan-save.md`

**File:** `.claude/commands/erk/plan-save.md`

**Change** — Line 118: Replace the stale description:
```
This atomically fetches the issue body, finds the matching step row, updates the PR cell, resets the Status cell to `-` (inference will determine `in_progress` from the `plan #` prefix), and writes the updated body back.
```
Replace with:
```
This atomically fetches the issue body, finds the matching step row, updates the PR cell, sets the Status cell to the computed display value (`in-progress` for `plan #` prefix, `done` for `#` prefix), and writes the updated body back.
```

### Step 3: Add Check 6 — Stale Display Status Detection

**File:** `src/erk/cli/commands/objective/check_cmd.py`

The `RoadmapStep` dataclass doesn't preserve the raw status cell value (the parser normalizes it). To detect stale `-` in the markdown, use a regex scan on `issue.body` (available at line 95 as the argument to `parse_roadmap`).

**Insert after line 162** (after Check 5, before `summary = compute_summary(phases)`):

```python
# Check 6: No stale display statuses (steps with PRs should have explicit status)
stale_pattern = re.compile(r"\|[^|]+\|[^|]+\|\s*-\s*\|\s*(?:#\d+|plan #\d+)\s*\|")
stale_matches = stale_pattern.findall(issue.body)
if not stale_matches:
    checks.append((True, "No stale display statuses"))
else:
    checks.append(
        (False, f"Stale '-' status with PR reference: {len(stale_matches)} step(s)")
    )
```

Also add `import re` at the top of the file (line ~3, after `from pathlib import Path`).

Update the docstring (lines 67-72) to add Check 6:
```
6. No stale display statuses (steps with PRs should have explicit status, not '-')
```

**Test file:** `tests/unit/cli/commands/objective/test_check_cmd.py`
- Add test case with a roadmap containing `| 1.1 | Do thing | - | #123 |` — should fail Check 6
- Add test case with `| 1.1 | Do thing | done | #123 |` — should pass Check 6

## Verification

1. Run `pytest tests/unit/cli/commands/objective/test_check_cmd.py` to verify Check 6 tests pass
2. Run `ruff check` and `ty check` on modified files
3. Review the two command files manually to confirm the wording is correct and consistent with `update_roadmap_step.py` behavior