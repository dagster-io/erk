# Plan: Address PR #8156 Review Comments

## Context

PR #8156 ("Targeted plan fetching by issue number for objective plans modal") received 6 automated review comments. 4 are local code quality fixes, 2 are cross-cutting test coverage suggestions.

## Batch 1: Local Fixes (auto-proceed)

### Fix 1: Remove silent exception swallowing (real.py:1417-1422)

**File:** `packages/erk-shared/src/erk_shared/gateway/github/real.py`

The existing `get_issues_with_pr_linkages` (line 1212-1214) does NOT wrap in try/except — it lets exceptions propagate. The new `get_issues_by_numbers_with_pr_linkages` inconsistently catches and silently swallows 5 exception types. The caller (`ObjectivePlansScreen._fetch_plans`) already has its own error boundary that catches all exceptions and displays them in the UI.

**Fix:** Remove the try/except block, keeping just the three lines of business logic (matching the pattern of `get_issues_with_pr_linkages`):

```python
query = self._build_issues_by_numbers_query(issue_numbers, location.repo_id)
response = self._execute_batch_pr_query(query, location.root)
return self._parse_issues_by_numbers_response(response, location.repo_id)
```

### Fix 2: Explicit LBYL truthiness check (real.py:465)

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

Change `if self._ctx.global_config` → `if self._ctx.global_config is not None`.

### Fix 3: Remove unused `_errors` variable (objective_plans_screen.py:30)

**File:** `src/erk/tui/screens/objective_plans_screen.py`

Change `phases, _errors = parse_roadmap(objective_body)` → `phases, _ = parse_roadmap(objective_body)`.

### Fix 4: Fix `lstrip('#')` prefix removal (objective_plans_screen.py:35)

**File:** `src/erk/tui/screens/objective_plans_screen.py`

`lstrip('#')` removes ALL `#` characters from the left (character set removal), not just the prefix. Change to:

```python
num_str = node.pr[1:] if node.pr.startswith("#") else node.pr
```

## Batch 2: Cross-Cutting Test Coverage (user confirmation)

### Fix 5: Tests for `get_issues_by_numbers_with_pr_linkages`

The fake provider's `fetch_plans_by_ids` is already exercised through screen tests. The GitHub fake's `get_issues_by_numbers_with_pr_linkages` filters `_issues_data` by number — simple enough that a direct unit test adds marginal value. **Dismiss with explanation.**

### Fix 6: Tests for `fetch_plans_by_ids`

Same rationale — the fake is exercised via screen tests. The real provider requires integration-level mocking that's expensive. **Dismiss with explanation.**

## Verification

1. Run `make fast-ci` to verify all lint/format/type/test checks pass
2. Resolve all 6 review threads via `erk exec resolve-review-threads`
3. Push changes
