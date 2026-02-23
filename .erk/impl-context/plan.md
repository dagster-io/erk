# Plan: Rename "prepare" properties to "checkout" in next_steps.py

## Context

PR review feedback on #7981: "change all these variable names to not use the word 'prepare'. python artifacts should align with user-facing messaging." The format functions use "Checkout:" and "Implement:" as user-facing labels, but the underlying properties are named `prepare`, `prepare_and_implement`, etc.

## Rename Mapping

### IssueNextSteps

| Old Name | New Name |
|---|---|
| `prepare` | `checkout` |
| `prepare_and_implement` | `checkout_and_implement` |
| `prepare_new_slot` | `checkout_new_slot` |
| `prepare_new_slot_and_implement` | `checkout_new_slot_and_implement` |

### DraftPRNextSteps

| Old Name | New Name |
|---|---|
| `checkout_and_implement` (existing, branch-based) | `checkout_branch_and_implement` |
| `prepare` | `checkout` |
| `prepare_and_implement` | `checkout_and_implement` |
| `prepare_new_slot` | `checkout_new_slot` |
| `prepare_new_slot_and_implement` | `checkout_new_slot_and_implement` |

Note: The existing `checkout_and_implement` (which uses branch name directly) is renamed to `checkout_branch_and_implement` to avoid collision with the plan-number-based variant.

### Constants

| Old Name | New Name |
|---|---|
| `PREPARE_SLASH_COMMAND` | `CHECKOUT_SLASH_COMMAND` |

## Files to Modify

### 1. Source: `packages/erk-shared/src/erk_shared/output/next_steps.py`
- Rename all property definitions per mapping above
- Update format function bodies that reference `s.prepare`, `s.prepare_and_implement`, `s.prepare_new_slot_and_implement`
- Rename `PREPARE_SLASH_COMMAND` → `CHECKOUT_SLASH_COMMAND`

### 2. Tests: `packages/erk-shared/tests/unit/output/test_next_steps.py`
- Rename test functions and property references (e.g., `test_draft_pr_next_steps_prepare_uses_pr_number` → `test_draft_pr_next_steps_checkout_uses_pr_number`)
- Update `s.prepare` → `s.checkout` in assertions

### 3. Tests: `tests/unit/shared/test_next_steps.py`
- Rename test methods in `TestIssueNextSteps` (e.g., `test_prepare_uses_co` → `test_checkout_uses_co`)
- Rename test methods in `TestDraftPRNextSteps` (e.g., `test_prepare_uses_pr_number` → `test_checkout_uses_pr_number`)
- Update all `steps.prepare*` references to `steps.checkout*`
- Rename existing `test_checkout_and_implement_uses_branch_name` → `test_checkout_branch_and_implement_uses_branch_name`

### 4. Docs: `docs/learned/planning/next-steps-output.md`
- Update property table with new names

## Approach

Use libcst-refactor agent for systematic batch rename across all files, or manual edit since the scope is well-bounded (3 source/test files + 1 doc file).

## Verification

```bash
uv run pytest packages/erk-shared/tests/unit/output/test_next_steps.py tests/unit/shared/test_next_steps.py -v
```

Then run `make fast-ci` to verify no other references break.
