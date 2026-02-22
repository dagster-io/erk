# Plan: Rename issue_number to plan_number in plan_* exec scripts (Nodes 2.1 + 2.2)

Part of Objective #7724, Nodes 2.1 + 2.2

## Context

Objective #7724 renames `issue_number` → `plan_number` across plan-related code. Phase 1 (PR #7849) completed the rename in `implement_shared.py` and `implement.py`. This plan covers Phase 2: the 9 `plan_*` exec scripts and their tests.

Since erk is unreleased private software, breaking JSON output keys and CLI flags is acceptable.

## Scope

**In scope (9 scripts + 9 test files):**

| # | Script | Test | Notes |
|---|--------|------|-------|
| 1 | `plan_save.py` | `test_plan_save.py` | JSON keys only |
| 2 | `plan_save_to_issue.py` | `test_plan_save_to_issue.py` | Bridges `result.issue_number` from shared type |
| 3 | `plan_create_review_pr.py` | `test_plan_create_review_pr.py` | Dataclass + positional arg |
| 4 | `plan_review_complete.py` | `test_plan_review_complete.py` | Dataclass + positional arg |
| 5 | `plan_submit_for_review.py` | `test_plan_submit_for_review.py` | Dataclass + positional arg |
| 6 | `plan_update_issue.py` | `test_plan_update_issue.py` | `--issue-number` option → `--plan-number` |
| 7 | `plan_update_from_feedback.py` | `test_plan_update_from_feedback.py` | Dataclass + positional arg |
| 8 | `plan_create_review_branch.py` | `test_plan_create_review_branch.py` | Dataclass + positional arg |
| 9 | `plan_migrate_to_draft_pr.py` | `test_plan_migrate_to_draft_pr.py` | `"original_issue_number"` → `"original_plan_number"` |

**Out of scope:**
- `CreatePlanIssueResult.issue_number` / `.issue_url` in `erk_shared` (Phase 4)
- All other files outside the 9 plan_* scripts

## Rename Rules

### Python identifiers
- All local variables, parameters, function args: `issue_number` → `plan_number`
- Dataclass fields: `issue_number: int` → `plan_number: int` (affects `asdict()` JSON output)

### JSON output keys
- `"issue_number"` → `"plan_number"`
- `"issue_url"` → `"plan_url"`
- `"original_issue_number"` → `"original_plan_number"` (plan_migrate_to_draft_pr.py only)

### Click CLI interface
- Positional arguments: `@click.argument("issue_number", type=int)` → `@click.argument("plan_number", type=int)`
- Named option (plan_update_issue.py only): `--issue-number` → `--plan-number`

### Bridging shared type (plan_save_to_issue.py)
`CreatePlanIssueResult.issue_number` is NOT renamed in this phase. Where accessed:
```python
# Before:
if result.issue_number is not None:
    output["issue_number"] = result.issue_number

# After:
if result.issue_number is not None:  # shared type field stays
    output["plan_number"] = result.issue_number  # JSON key renamed
```

### Docstrings/comments
- Update references to `issue_number` in docstrings and comments within the target files only

## Implementation Order

Process each script+test pair sequentially to keep changes reviewable:

1. **plan_save.py** + test — simplest (JSON keys only, 2 `issue_number` + 1 `issue_url`)
2. **plan_update_issue.py** + test — unique `--issue-number` CLI option rename
3. **plan_migrate_to_draft_pr.py** + test — unique `original_issue_number` key
4. **plan_save_to_issue.py** + test — most complex (bridges shared type, 8 occurrences)
5. **plan_create_review_pr.py** + test — dataclass + positional arg pattern
6. **plan_review_complete.py** + test — same pattern as #5
7. **plan_submit_for_review.py** + test — same pattern
8. **plan_update_from_feedback.py** + test — same pattern
9. **plan_create_review_branch.py** + test — same pattern

After each pair, run the corresponding unit test to verify.

## Files to Modify

**Source files** (`src/erk/cli/commands/exec/scripts/`):
- `plan_save.py`
- `plan_save_to_issue.py`
- `plan_create_review_pr.py`
- `plan_review_complete.py`
- `plan_submit_for_review.py`
- `plan_update_issue.py`
- `plan_update_from_feedback.py`
- `plan_create_review_branch.py`
- `plan_migrate_to_draft_pr.py`

**Test files** (`tests/unit/cli/commands/exec/scripts/`):
- `test_plan_save.py`
- `test_plan_save_to_issue.py`
- `test_plan_create_review_pr.py`
- `test_plan_review_complete.py`
- `test_plan_submit_for_review.py`
- `test_plan_update_issue.py`
- `test_plan_update_from_feedback.py`
- `test_plan_create_review_branch.py`
- `test_plan_migrate_to_draft_pr.py`

## Verification

1. Run unit tests for each file pair after rename
2. Run full test suite for the exec scripts directory: `pytest tests/unit/cli/commands/exec/scripts/test_plan_*.py`
3. Run type checker on modified files
4. Run linter/formatter