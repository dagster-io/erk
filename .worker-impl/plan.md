# Plan: Convert `get_issue` to `IssueInfo | IssueNotFound` Discriminated Union

Part of Objective #6292, Steps 2.1–2.3

## Goal

Convert `get_issue` from raising `RuntimeError` when an issue is not found to returning `IssueInfo | IssueNotFound`, following the sentinel pattern established by `PRNotFound`. Update all ~25 callers to use `isinstance()` checks instead of `try/except RuntimeError`.

## Phase 1: Define `IssueNotFound` type (Step 2.1)

**File:** `packages/erk-shared/src/erk_shared/gateway/github/issues/types.py`

Add after `IssueInfo`:

```python
@dataclass(frozen=True)
class IssueNotFound:
    """Sentinel indicating an issue was not found.

    Used as part of union return types for LBYL-style error handling.
    """

    issue_number: int
```

Follows the sentinel pattern (no `success` field) since `get_issue` is a read/lookup operation.

## Phase 2: Update gateway layer (Step 2.2)

Update return type to `IssueInfo | IssueNotFound` in 4 files:

### abc.py

`packages/erk-shared/src/erk_shared/gateway/github/issues/abc.py`

- Change return type on `get_issue` signature (line 58)
- Update docstring: remove `Raises: RuntimeError` section, update `Returns` to mention `IssueNotFound`
- Add `IssueNotFound` to imports

### real.py

`packages/erk-shared/src/erk_shared/gateway/github/issues/real.py`

- Change return type (line 134)
- Wrap `execute_gh_command_with_retry` call in `try/except RuntimeError` → `return IssueNotFound(issue_number=number)`
- Add `IssueNotFound` to imports

### fake.py

`packages/erk-shared/src/erk_shared/gateway/github/issues/fake.py`

- Change return type (line 177)
- Replace `raise RuntimeError(msg)` with `return IssueNotFound(issue_number=number)`
- Add `IssueNotFound` to imports

### dry_run.py

`packages/erk-shared/src/erk_shared/gateway/github/issues/dry_run.py`

- Change return type (line 46)
- No logic change (delegates to wrapped)
- Add `IssueNotFound` to imports

**Note:** No `PrintingGitHubIssues` exists — `PrintingGitHub.issues` delegates the whole sub-gateway.

## Phase 3: Update all callers (Step 2.3)

~25 call sites grouped by error handling pattern:

### Group A: `try/except RuntimeError` at exec script boundary (10 files)

Convert `try/except RuntimeError` → `isinstance(issue, IssueNotFound)` check.

| File                                                              | Line |
| ----------------------------------------------------------------- | ---- |
| `src/erk/cli/commands/exec/scripts/get_issue_body.py`             | 34   |
| `src/erk/cli/commands/exec/scripts/update_dispatch_info.py`       | 66   |
| `src/erk/cli/commands/exec/scripts/plan_update_issue.py`          | 95   |
| `src/erk/cli/commands/exec/scripts/mark_impl_started.py`          | 142  |
| `src/erk/cli/commands/exec/scripts/mark_impl_ended.py`            | 142  |
| `src/erk/cli/commands/exec/scripts/plan_submit_for_review.py`     | 66   |
| `src/erk/cli/commands/exec/scripts/get_plan_metadata.py`          | 62   |
| `src/erk/cli/commands/exec/scripts/update_plan_remote_session.py` | 113  |
| `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py`            | 58   |
| `src/erk/cli/commands/exec/scripts/update_issue_body.py`          | 65   |

### Group B: `try/except RuntimeError` in CLI commands (5 files)

| File                                              | Line | Current pattern                  |
| ------------------------------------------------- | ---- | -------------------------------- |
| `src/erk/cli/commands/plan/learn/complete_cmd.py` | 36   | try/except → ClickException      |
| `src/erk/cli/commands/plan/check_cmd.py`          | 72   | try/except → PlanValidationError |
| `src/erk/cli/commands/submit.py`                  | 336  | try/except → SystemExit(1)       |
| `src/erk/cli/commands/objective_helpers.py`       | 48   | try/except → return False        |
| `src/erk/cli/commands/objective_helpers.py`       | 103  | try/except → return None         |

### Group C: `try/except RuntimeError` in shared library (2 files)

| File                                                                    | Line    | Migration                    |
| ----------------------------------------------------------------------- | ------- | ---------------------------- |
| `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` | 176     | isinstance → continue (skip) |
| `src/erk/core/plan_context_provider.py`                                 | 80, 135 | isinstance → return None     |

### Group D: Pre-checked with `issue_exists()` then bare call (5 files)

These already LBYL with `issue_exists()`. Add defensive `isinstance` check after the `get_issue` call.

| File                                                             | Line |
| ---------------------------------------------------------------- | ---- |
| `src/erk/cli/commands/exec/scripts/plan_review_complete.py`      | 100  |
| `src/erk/cli/commands/exec/scripts/plan_create_review_branch.py` | 87   |
| `src/erk/cli/commands/exec/scripts/plan_update_from_feedback.py` | 86   |
| `src/erk/cli/commands/tripwire_promotion_helpers.py`             | 51   |
| `src/erk/cli/commands/land_cmd.py`                               | 516  |

### Group E: Bare calls (no error handling) (7 files)

Add `isinstance(issue, IssueNotFound)` check with appropriate error handling.

| File                                              | Line | Context                        |
| ------------------------------------------------- | ---- | ------------------------------ |
| `src/erk/cli/commands/objective/close_cmd.py`     | 34   | user_output error + return     |
| `src/erk/cli/commands/objective/reconcile_cmd.py` | 35   | click.echo + SystemExit(1)     |
| `src/erk/cli/commands/pr/metadata_helpers.py`     | 54   | early return (non-critical)    |
| `src/erk/cli/commands/submit.py`                  | 179  | return None                    |
| `src/erk/cli/commands/submit.py`                  | 749  | inside try block, non-critical |
| `src/erk/cli/commands/submit.py`                  | 900  | pre-checked with issue_exists  |
| `src/erk/cli/commands/land_cmd.py`                | 298  | needs error handling added     |
| `src/erk/cli/commands/review_pr_cleanup.py`       | 42   | return None (non-critical)     |

### Group F: `try/except (RuntimeError, ValueError)` broad catches (2 call sites)

| File                                               | Line |
| -------------------------------------------------- | ---- |
| `src/erk/cli/commands/exec/scripts/impl_signal.py` | 253  |
| `src/erk/cli/commands/exec/scripts/impl_signal.py` | 341  |

Add `isinstance` check before accessing `issue.body`. Keep the outer `try/except ValueError` for the `update_plan_header_*` calls.

### Group G: Shared library bare calls (3 files)

| File                                                       | Line | Migration                                           |
| ---------------------------------------------------------- | ---- | --------------------------------------------------- |
| `packages/erk-shared/src/erk_shared/plan_store/github.py`  | 104  | isinstance → raise RuntimeError (preserve contract) |
| `packages/erk-shared/src/erk_shared/plan_store/github.py`  | 376  | isinstance → raise RuntimeError (preserve contract) |
| `packages/erk-shared/src/erk_shared/sessions/discovery.py` | 111  | isinstance → raise RuntimeError (preserve contract) |

### Group H: Exec scripts with bare calls (2 files)

| File                                                          | Line | Migration                                      |
| ------------------------------------------------------------- | ---- | ---------------------------------------------- |
| `src/erk/cli/commands/exec/scripts/track_learn_evaluation.py` | 114  | Add isinstance check + JSON error output       |
| `src/erk/cli/commands/exec/scripts/track_learn_result.py`     | 150  | Add isinstance check + JSON error output       |
| `src/erk/cli/commands/exec/scripts/upload_session.py`         | 130  | Add isinstance check inside existing try block |
| `src/erk/cli/commands/exec/scripts/plan_create_review_pr.py`  | 128  | Add isinstance → raise CreateReviewPRException |

## Phase 4: Update tests

- Update fake tests to assert `isinstance(result, IssueNotFound)` instead of `pytest.raises(RuntimeError)`
- Verify all exec script tests pass (they test JSON output / exit codes, not exception types)
- Run full test suite

## Verification

1. Run `make fast-ci` (unit tests, ty, ruff, prettier)
2. Verify no remaining `except RuntimeError` catches that reference `get_issue`
3. Grep for `\.get_issue\(` and confirm every call site handles `IssueNotFound`
