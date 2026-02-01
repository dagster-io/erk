# Address PR #6500 Review Feedback

## Batch 1: Local Fix (auto-proceed)

| # | Location | Summary |
|---|----------|---------|
| 1 | `trigger_async_learn.py:164` | Move `planning_session_id` closer to its use site |

**Thread**: `PRRT_kwDOPxC3hc5sElm4`

**Change**: Move `planning_session_id = sessions_result.get("planning_session_id")` from line 164 (before the loop) to just before line 179 where it's used in the conditional. Since it only depends on `sessions_result` (not loop state), it can be moved inside the loop right before the comparison, or kept just outside but closer. The cleanest option: move it to just before the `prefix = ...` line inside the loop body.

**File**: `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`

## Batch 2: Discussion Comment (complex)

| # | Comment | Summary |
|---|---------|---------|
| 1 | comment_id 3830893195 | Present options for stricter schema enforcement |

**Action**: Reply to the discussion comment with a substantive analysis of options. Based on exploration:

### Options to Present

1. **Move `GetLearnSessionsResult` to `erk_shared` as a TypedDict** — creates a single source of truth for the response schema. Both scripts import the same type. Consumer uses `cast()` for type narrowing. Provides static type safety but no runtime validation.

2. **Add a `TypeGuard` validator function in `erk_shared`** — a `validate_get_learn_sessions_result()` function that checks all required fields exist with correct types. Follows erk's LBYL pattern. Provides both static type narrowing and runtime safety. More code but catches mismatches at runtime with clear error messages.

3. **Keep current pattern, add a shared constant for field names** — minimal change: define field name constants (`SOURCE_TYPE_FIELD = "source_type"` etc.) in `erk_shared` and use them in both scripts. Prevents typos but doesn't add structural validation.

**Recommendation in reply**: Option 2 is strongest but significant work. Option 1 is the pragmatic middle ground. Note this is a broader pattern across all exec scripts using `_run_subprocess` — none currently validate input schemas.

This is a **reply-only** action (no code changes). The reply will present the options for the reviewer to decide on as a follow-up.

## Verification

1. Run `pytest tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py -v` — all 5 tests pass
2. Run `ty check` on modified source file — clean
3. Run `make fast-ci` — all checks pass
4. Verify all threads resolved via `/pr-feedback-classifier`