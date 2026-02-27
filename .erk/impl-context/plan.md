# Plan: Failing Checks Modal for erk dash

## Context

The erk dash TUI has a "c" keybinding that opens a modal showing unresolved PR review comments. This plan adds a similar "h" keybinding that opens a modal showing **failing CI checks** for the selected PR. This enables quick diagnosis of CI failures without leaving the dashboard.

## Changes

### 1. Add `PRCheckRun` data type

**File:** `packages/erk-shared/src/erk_shared/gateway/github/types.py`

Add a frozen dataclass after `PRReviewThread`:

```python
@dataclass(frozen=True)
class PRCheckRun:
    name: str           # e.g., "CI / unit-tests"
    status: str         # "completed", "in_progress", "queued", "pending"
    conclusion: str | None  # "success", "failure", "cancelled", etc. None if not completed
    detail_url: str | None  # URL to check run detail page
```

### 2. Add GraphQL query for check run details

**File:** `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py`

New query constant `GET_PR_CHECK_RUNS_QUERY` that fetches `statusCheckRollup.contexts(first: 100)` with `__typename`, name/context, status/state, conclusion, and detail URLs for both `CheckRun` and `StatusContext` union types.

### 3. Add `get_pr_check_runs` to GitHub gateway (5-place pattern)

All in `packages/erk-shared/src/erk_shared/gateway/github/`:

| File | Implementation |
|------|---------------|
| `abc.py` | Abstract method `get_pr_check_runs(repo_root, pr_number) -> list[PRCheckRun]` |
| `real.py` | GraphQL query + parse response, filter to failing only, sort by name |
| `fake.py` | Dict storage `_pr_check_runs`, setter method `set_pr_check_runs()` |
| `dry_run.py` | Delegate to wrapped (read-only) |
| `printing.py` | Delegate to wrapped (read-only, no printing) |

The real implementation parses both `CheckRun` and `StatusContext` node types from the GraphQL union response.

### 4. Add `fetch_check_runs` to PlanDataProvider (3-place pattern)

| File | Implementation |
|------|---------------|
| `packages/.../plan_data_provider/abc.py` | Abstract method `fetch_check_runs(pr_number) -> list[PRCheckRun]` |
| `packages/.../plan_data_provider/real.py` | Delegates to `ctx.github.get_pr_check_runs()` |
| `packages/.../plan_data_provider/fake.py` | Dict storage + setter, return `[]` by default |

### 5. Add raw check fields to `PlanRowData`

**File:** `src/erk/tui/data/types.py`

Add two fields after `checks_display`:
- `checks_passing: bool | None` — for LBYL guards in the action handler
- `checks_counts: tuple[int, int] | None` — for the modal header summary

### 6. Populate raw check fields in row builder

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

In `_build_row_data`, extract `checks_passing` and `checks_counts` from `selected_pr` and pass to the `PlanRowData` constructor.

### 7. Update `make_plan_row` test helper

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`

Add `checks_passing: bool | None` and `checks_counts: tuple[int, int] | None` parameters (with `None` defaults in the helper since it's a test factory, not a domain constructor).

### 8. Create `CheckRunsScreen` modal

**File:** `src/erk/tui/screens/check_runs_screen.py` (new)

Follow the exact pattern of `unresolved_comments_screen.py`:
- `ModalScreen` subclass with escape/q/space dismiss bindings
- `@work(thread=True)` fetch via `provider.fetch_check_runs(pr_number)`
- `call_from_thread()` callback updates UI
- `_format_check_runs()` renders failing checks as markdown list with name, conclusion, and detail URL as link
- CSS IDs prefixed with `checks-` (dialog, header, title, summary, divider, content-container, footer, loading, empty, error)

### 9. Add keybinding and action handler

**File:** `src/erk/tui/app.py`

- Binding: `Binding("h", "view_checks", "Checks", show=False)`
- Import: `from erk.tui.screens.check_runs_screen import CheckRunsScreen`
- Action handler `action_view_checks()` with LBYL guards:
  1. `row is None` → return
  2. `row.pr_number is None` → status message "No PR linked to this plan"
  3. `row.checks_passing is None` → status message "No checks available"
  4. `row.checks_passing is True` → status message "All checks passing"
  5. Otherwise → push `CheckRunsScreen`

### 10. Update help screen

**File:** `src/erk/tui/screens/help_screen.py`

Add `h` to the Actions section: "View failing checks"

## Verification

1. Run `make fast-ci` to ensure all existing tests pass
2. Run `erk dash -i`, select a PR with failing checks, press `h` — modal should show failing check names with links
3. Press `h` on a PR with all checks passing — status bar should show "All checks passing"
4. Press `h` on a row with no PR — status bar should show "No PR linked to this plan"
5. Run new unit tests for `_format_check_runs()` and `action_view_checks` guards
