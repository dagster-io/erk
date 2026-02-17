# Plan: Objective #7129 Step 3.1 — Eliminate `find_sessions_for_plan` monkeypatching

Part of Objective #7129, Step 3.1

## Context

`tests/unit/cli/commands/land/test_learn_status.py` has 14 `monkeypatch.setattr(land_cmd, "find_sessions_for_plan", ...)` calls. These intercept a function that **already accepts `GitHubIssues` as a parameter** — `find_sessions_for_plan(github: GitHubIssues, ...)`. The tests already create `FakeGitHubIssues` and pass it via `context_for_test(issues=fake_issues)`, but then redundantly monkeypatch the function to bypass the real call.

The fix requires **zero production code changes**. The existing dependency injection is sufficient — we just need the test issues' plan header metadata to contain the right session IDs so `find_sessions_for_plan` returns the correct `SessionsForPlan` when running against the fake.

## Approach

`find_sessions_for_plan` extracts session data from:
1. Plan header metadata in the issue body (via `extract_plan_header_*` functions)
2. Issue comments (via `extract_implementation_sessions` / `extract_learn_sessions`)

The test helper `format_plan_header_body_for_test()` already supports `created_from_session`, `last_local_impl_session`, and `last_learn_session` keyword arguments. By setting these, `find_sessions_for_plan` running against `FakeGitHubIssues` will return the exact `SessionsForPlan` the tests need.

## Implementation

### Phase 1: Update tests that need learn sessions found (5 tests)

These tests mock `find_sessions_for_plan` to return `learn_session_ids=["learn-session-1"]`. Instead, configure the plan header body with `last_learn_session="learn-session-1"`.

**File:** `tests/unit/cli/commands/land/test_learn_status.py`

| Test | Line | Change |
|------|------|--------|
| `test_check_learn_status_and_prompt_skips_when_already_learned` | 61 | Add `created_from_session="plan-session-1"`, `last_local_impl_session="impl-session-1"`, `last_learn_session="learn-session-1"` to `format_plan_header_body_for_test()`. Remove monkeypatch. Remove `monkeypatch` fixture. |
| `test_check_learn_status_and_prompt_runs_when_config_enabled` | 400 | Same plan header changes. Remove monkeypatch. Remove `monkeypatch` fixture. |
| `test_check_learn_status_null_with_sessions_shows_success` | 556 | Add `last_learn_session="learn-session-1"` to existing `format_plan_header_body_for_test(learn_status=None)`. Remove monkeypatch. Remove `monkeypatch` fixture. |

### Phase 2: Update tests that need no learn sessions (6 tests)

These tests mock `find_sessions_for_plan` to return `learn_session_ids=[]`. The default `format_plan_header_body_for_test()` already produces a body with no `last_learn_session`, so `find_sessions_for_plan` will naturally return empty learn sessions. Just remove the monkeypatch.

| Test | Line | Change |
|------|------|--------|
| `test_check_learn_status_and_prompt_warns_when_not_learned` | 140 | Remove monkeypatch. Keep `monkeypatch` (still used for `click.prompt`). |
| `test_check_learn_status_and_prompt_cancels_when_user_declines` | 199 | Same. |
| `test_check_learn_status_and_prompt_outputs_script_when_user_declines` | 261 | Same. |
| `test_check_learn_status_null_no_sessions_triggers_async_in_non_interactive` | 606 | Remove find_sessions monkeypatch. Keep `monkeypatch` (still used for `subprocess.Popen`). |
| `test_check_learn_status_and_prompt_manual_learn_preprocesses_and_continues` | 678 | Remove find_sessions monkeypatch. Keep `monkeypatch` (still used for `click.prompt` and `_preprocess_and_prepare_manual_learn`). |
| `test_option4_calls_preprocess_and_continues_landing` | 876 | Same as above. |

### Phase 3: Update tests with early returns (5 tests)

These tests monkeypatch `find_sessions_for_plan` as a safety net — the function is never actually called due to early returns. Just remove the monkeypatch.

| Test | Line | Change |
|------|------|--------|
| `test_check_learn_status_and_prompt_skips_when_force` | 90 | Remove monkeypatch, `find_sessions_called` tracking, and assertion. Remove `monkeypatch` fixture. |
| `test_check_learn_status_and_prompt_skips_for_learn_plans` | 320 | Same. Remove `monkeypatch` fixture. |
| `test_check_learn_status_and_prompt_skips_when_config_disabled` | 348 | Same. Remove `monkeypatch` fixture. |
| `test_check_learn_status_completed_shows_success` | 453 | Same. Remove `monkeypatch` fixture. |
| `test_check_learn_status_pending_shows_progress` | 499 | Same. Remove `monkeypatch` fixture. |

### Phase 4: Clean up imports

After removing all 14 monkeypatch calls:
- Remove `from erk.cli.commands import land_cmd` (line 10) — only used as monkeypatch target
- Keep all other imports (they're used by remaining tests and remaining monkeypatches for `click.prompt`, `subprocess.Popen`, `_preprocess_and_prepare_manual_learn`)

**Wait — check first:** `land_cmd` import may still be needed for the `_preprocess_and_prepare_manual_learn` monkeypatches at lines 690 and 888. Verify before removing.

## Out of Scope

These monkeypatches in the same file are **not** addressed by this step:
- `click.prompt` (5 instances) — mocks third-party UI library
- `subprocess.Popen` (2 instances) — mocks subprocess for `_trigger_async_learn`
- `_preprocess_and_prepare_manual_learn` (2 instances) — separate function mock

## Files Modified

1. `tests/unit/cli/commands/land/test_learn_status.py` — remove 14 monkeypatches, update plan header bodies, clean up fixtures
2. **No production code changes**

## Verification

1. Run targeted tests: `uv run pytest tests/unit/cli/commands/land/test_learn_status.py -v`
2. Confirm all 14+ tests pass
3. Run broader land tests: `uv run pytest tests/unit/cli/commands/land/ -v`
4. Run type checker on test file
5. Verify no remaining `find_sessions_for_plan` monkeypatches: grep the test file