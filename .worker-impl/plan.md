# Plan: Update Learn Skill to Handle Remote Sessions

**Part of Objective #4991, Step 2.5**

## Goal

Enable the `/erk:learn` skill to download and process sessions from remote GitHub Actions implementations. Currently, the skill identifies remote sessions but skips them with a placeholder message.

## Current State

- **`get-learn-sessions`**: Returns `session_sources` with only `LocalSessionSource` objects. Remote implementation metadata (`last_remote_impl_run_id`, `last_remote_impl_session_id`) is returned as separate fields but NOT in `session_sources`.
- **`RemoteSessionSource`**: Class exists at `packages/erk-shared/src/erk_shared/learn/extraction/session_source.py` but is never used.
- **`download-remote-session`**: Exec command exists and works, downloads artifacts to `.erk/scratch/remote-sessions/{session_id}/session.jsonl`.
- **`learn.md`**: Says "If `source_type == "remote"`: Skip for now".

## Implementation Phases

### Phase 1: Update `get-learn-sessions` to Return Remote Sessions

**File:** `src/erk/cli/commands/exec/scripts/get_learn_sessions.py`

1. **Add import for `RemoteSessionSource` and `SessionSource`**:
   ```python
   from erk_shared.learn.extraction.session_source import (
       LocalSessionSource,
       RemoteSessionSource,
       SessionSource,
       SessionSourceDict,
   )
   ```

2. **Update `_build_result` parameter type** (line ~113):
   ```python
   session_sources: list[SessionSource],  # was list[LocalSessionSource]
   ```

3. **Update `_discover_sessions` variable type** (line ~168):
   ```python
   session_sources: list[SessionSource] = [...]  # was list[LocalSessionSource]
   ```

4. **Add remote session to `session_sources`** (after line ~186):
   ```python
   # Add remote session source if remote implementation exists
   if sessions_for_plan.last_remote_impl_session_id is not None:
       if sessions_for_plan.last_remote_impl_run_id is not None:
           remote_source = RemoteSessionSource(
               session_id=sessions_for_plan.last_remote_impl_session_id,
               run_id=sessions_for_plan.last_remote_impl_run_id,
               path=None,  # Path is None until downloaded
           )
           session_sources.append(remote_source)
   ```

### Phase 2: Update Learn Skill Documentation

**File:** `.claude/commands/erk/learn.md`

1. **Update Step 1 documentation** (~line 40): Clarify that `path` is null for remote sessions until downloaded.

2. **Update Step 3 preprocessing section** (~line 134-158): Replace "skip for now" with download instructions:

   For `source_type == "remote"`:
   1. Call `erk exec download-remote-session --run-id "<run_id>" --session-id "<session_id>"`
   2. Parse JSON output to get `path`
   3. If success, preprocess using the returned path
   4. If failure (artifact expired, permissions, etc.), inform user and skip

3. **Update "Note on remote implementations"** (~line 55): Remove "In Phase 1" caveat, describe new capability.

### Phase 3: Add Tests

**File:** `tests/unit/cli/commands/exec/scripts/test_get_learn_sessions.py`

Use the existing test helper `format_plan_header_body_for_test` from `tests/test_utils/plan_helpers.py` which already supports `last_remote_impl_run_id` and `last_remote_impl_session_id`.

1. **Test `session_sources` includes remote session**:
   - Create issue with `format_plan_header_body_for_test(last_remote_impl_run_id="12345", last_remote_impl_session_id="remote-abc")`
   - Verify `session_sources` contains a `RemoteSessionSource` with `source_type: "remote"`, correct `run_id`/`session_id`, and `path: null`

2. **Test mixed local and remote sessions**:
   - Set up `FakeClaudeInstallation` with local sessions AND plan header with remote metadata
   - Verify `session_sources` list contains both `source_type: "local"` and `source_type: "remote"` entries

## Critical Files

| File | Action |
|------|--------|
| `src/erk/cli/commands/exec/scripts/get_learn_sessions.py` | Modify - add RemoteSessionSource to session_sources |
| `.claude/commands/erk/learn.md` | Modify - update preprocessing instructions |
| `tests/unit/cli/commands/exec/scripts/test_get_learn_sessions.py` | Modify - add remote session tests |
| `tests/test_utils/plan_helpers.py` | Reference - use `format_plan_header_body_for_test` |
| `packages/erk-shared/src/erk_shared/learn/extraction/session_source.py` | Reference - `RemoteSessionSource` class |

## Design Decisions

1. **Remote sessions added to `session_sources` with `path=None`**: Maintains consistent abstraction; skill detects null path and downloads on demand.

2. **On-demand download**: Sessions downloaded during learn, not eagerly, avoiding unnecessary API calls.

3. **Graceful failure handling**: If artifact expired (90-day retention) or download fails, inform user and continue with available sessions.

## Verification

1. **Unit tests**: Run `pytest tests/unit/cli/commands/exec/scripts/test_get_learn_sessions.py -v`

2. **Manual test with remote implementation**:
   - Find a plan that was implemented remotely (has `last_remote_impl_at` in plan-header)
   - Run `erk exec get-learn-sessions <issue-number>`
   - Verify output has `session_sources` with a `source_type: "remote"` entry
   - Run `/erk:learn <issue-number>` and verify it attempts to download and process the remote session

3. **Type checking**: Run `make ty` to verify type annotations are correct

## Related Documentation

- Skills: `fake-driven-testing` (test patterns)
- Docs: `docs/learned/sessions/layout.md`, `docs/learned/planning/`