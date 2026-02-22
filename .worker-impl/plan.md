# Replan: Rename issue_number to plan_number in plan_* exec scripts

Part of Objective #7724

## Context

Original plan (#7882) targeted 9 plan_* exec scripts. Since then, PR #7838 removed the plan review PR feature, deleting 4 scripts:
- plan_create_review_pr.py
- plan_review_complete.py
- plan_submit_for_review.py
- plan_create_review_branch.py

The remaining 5 scripts still have `issue_number` identifiers and JSON keys that need renaming.

## Scope

**5 scripts + 5 test files:**

| # | Script | Test | Key Changes |
|---|--------|------|-------------|
| 1 | `plan_save.py` | `test_plan_save.py` | JSON keys `"issue_number"` → `"plan_number"`, `"issue_url"` → `"plan_url"` (variable already renamed) |
| 2 | `plan_update_issue.py` | `test_plan_update_issue.py` | `--issue-number` CLI option → `--plan-number`, parameter + JSON keys |
| 3 | `plan_migrate_to_draft_pr.py` | `test_plan_migrate_to_draft_pr.py` | Click argument, `"original_issue_number"` → `"original_plan_number"`, all Python identifiers |
| 4 | `plan_save_to_issue.py` | `test_plan_save_to_issue.py` | Bridges `result.issue_number` from shared type (shared field stays, JSON keys renamed) |
| 5 | `plan_update_from_feedback.py` | `test_plan_update_from_feedback.py` | Dataclass field, Click argument, all Python identifiers |

## Rename Rules

### Python identifiers
- Local variables, parameters, function args: `issue_number` → `plan_number`
- Dataclass fields: `issue_number: int` → `plan_number: int`

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
# shared type field stays as-is
if result.issue_number is not None:
    output["plan_number"] = result.issue_number  # JSON key renamed
```

### Docstrings/comments
- Update references to `issue_number` in docstrings and comments within the target files only

## Implementation Order

1. **plan_save.py** + test — simplest (2 JSON key renames, variable already `plan_number`)
2. **plan_update_issue.py** + test — `--issue-number` CLI option rename + parameter + JSON keys
3. **plan_migrate_to_draft_pr.py** + test — Click argument + `original_issue_number` + all identifiers
4. **plan_save_to_issue.py** + test — bridges shared type, most occurrences (15+)
5. **plan_update_from_feedback.py** + test — dataclass field + Click argument + identifiers

After each pair, run the corresponding unit test to verify.

## Files to Modify

**Source files** (`src/erk/cli/commands/exec/scripts/`):
- `plan_save.py`
- `plan_update_issue.py`
- `plan_migrate_to_draft_pr.py`
- `plan_save_to_issue.py`
- `plan_update_from_feedback.py`

**Test files** (`tests/unit/cli/commands/exec/scripts/`):
- `test_plan_save.py`
- `test_plan_update_issue.py`
- `test_plan_migrate_to_draft_pr.py`
- `test_plan_save_to_issue.py`
- `test_plan_update_from_feedback.py`

## Verification

1. Run unit tests for each file pair after rename
2. Run full test suite: `pytest tests/unit/cli/commands/exec/scripts/test_plan_*.py`
3. Run type checker on modified files
4. Run linter/formatter
