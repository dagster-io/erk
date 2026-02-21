# Replace Session Gist Archival with Branch-Based Storage

## Context

After PR #7733 replaced gist transport for _learn materials_, the session gist archival system is the last remaining gist dependency. When `plan-implement.yml` completes a remote implementation, it uploads the full session JSONL to a secret GitHub gist, then `trigger_async_learn.py` (during `erk land`) downloads it from the gist for preprocessing. This has several problems: no cleanup (gists accumulate forever), uncompressed uploads (100MB+ sessions), authentication gaps (secret gists via `gh` but unauthenticated `urllib` downloads), and rate limits.

This plan replaces the gist with the same branch-based pattern: CI commits the session to a `session/{plan_id}` branch, consumers fetch it via `git.remote.fetch_branch()` + `git show`, and the branch is cleaned up after consumption. This also allows removing `create_gist` from the GitHub gateway ABC entirely (nothing else uses it).

## Changes

### 1. Replace `upload_session.py` with branch-based storage

**File:** `src/erk/cli/commands/exec/scripts/upload_session.py`

Replace the `create_gist()` call with the branch creation pattern from `trigger_async_learn.py`:

- Create `session/{plan_id}` branch from `origin/master`
- Copy session JSONL to `.erk/session/{session_id}.jsonl` on that branch
- Commit and force-push (force for re-implementation idempotency)
- Restore original branch in `finally` block
- Store `last_session_branch` (not `gist_url`/`gist_id`) on plan metadata

Needs access to git gateway — add `require_git(ctx)` alongside existing `require_github(ctx)`.

Metadata fields stored on plan header:

- `last_session_branch` (replaces `last_session_gist_url` + `last_session_gist_id`)
- `last_session_id` (unchanged)
- `last_session_at` (unchanged)
- `last_session_source` (unchanged)

Output JSON changes: `gist_id`/`gist_url`/`raw_url` → `session_branch`.

### 2. Replace `download_remote_session.py` with branch-based download

**File:** `src/erk/cli/commands/exec/scripts/download_remote_session.py`

Replace `--gist-url` option with `--session-branch`:

- `git.remote.fetch_branch(repo_root, "origin", session_branch)` to fetch
- Extract file via subprocess: `git show origin/{session_branch}:.erk/session/{session_id}.jsonl`
- Write to same output location: `.erk/scratch/remote-sessions/{session_id}/session.jsonl`
- Remove `normalize_gist_url()`, `_download_from_gist()`, urllib imports
- Add `require_git(ctx)` for gateway access
- Output JSON: `"source": "branch"` (was `"gist"`)

### 3. Update `trigger_async_learn.py` remote session download

**File:** `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`

Update `_download_remote_session_for_learn()`:

- Replace `gist_url: str` param with `session_branch: str`
- Use `git.remote.fetch_branch()` + subprocess `git show` (same pattern as download script)
- Remove `normalize_gist_url` import from `download_remote_session`
- Update caller at ~line 454-468: read `session_branch` from source item instead of `gist_url`

Add session branch cleanup after learn branch is created and pushed (~line 625):

```python
# Clean up session branch after materials are on learn branch
subprocess.run(
    ["git", "push", "origin", "--delete", session_branch],
    cwd=str(repo_root), capture_output=True,
)
```

### 4. Update `get_learn_sessions.py` session source discovery

**File:** `src/erk/cli/commands/exec/scripts/get_learn_sessions.py`

Lines 168-193: Replace gist-based remote source with branch-based:

- Check `sessions_for_plan.last_session_branch` instead of `last_session_gist_url`
- Build `RemoteSessionSource` with `session_branch=` instead of `gist_url=`

Output fields: Replace `last_session_gist_url` with `last_session_branch` in `_build_result()` (line 105).

### 5. Update `RemoteSessionSource` dataclass

**File:** `packages/erk-shared/src/erk_shared/learn/extraction/session_source.py` (line 151)

- Replace `gist_url: str | None` with `session_branch: str | None`
- Update `__slots__`, `__init__`, property, `to_dict()`

### 6. Update `GetLearnSessionsResultDict`

**File:** `packages/erk-shared/src/erk_shared/learn/extraction/get_learn_sessions_result.py`

- Replace `last_session_gist_url` with `last_session_branch`

### 7. Update `SessionsForPlan` dataclass

**File:** `packages/erk-shared/src/erk_shared/sessions/discovery.py` (line 19)

- Replace `last_session_gist_url: str | None` with `last_session_branch: str | None`

### 8. Update plan header metadata schema

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`

- Remove `LAST_SESSION_GIST_URL` and `LAST_SESSION_GIST_ID` field definitions (~lines 383-384)
- Add `LAST_SESSION_BRANCH` field definition
- Update `VALID_PLAN_HEADER_FIELDS` list
- Update validation block: remove gist_url/gist_id validation, add session_branch validation

### 9. Update plan header extractors

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py`

- Remove `extract_plan_header_session_gist_url()` and `extract_plan_header_session_gist_id()`
- Add `extract_plan_header_session_branch()`
- Update `update_plan_header_session_gist()` → `update_plan_header_session_branch()`
- Update `find_sessions_for_plan()` in `backend.py` to use new extractors

### 10. Update `plan_store/backend.py`

**File:** `packages/erk-shared/src/erk_shared/plan_store/backend.py`

Update `find_sessions_for_plan()` (~lines 240-245):

- Replace `extract_plan_header_session_gist_url` call with `extract_plan_header_session_branch`
- Update `SessionsForPlan` construction

### 11. Remove `create_gist` from GitHub gateway

Since `upload_session.py` was the only consumer of `create_gist`:

- **`abc.py`**: Remove `create_gist` abstract method, `GistCreated`, `GistCreateError` types
- **`real.py`**: Remove `create_gist` implementation
- **`fake.py`**: Remove `create_gist` implementation and `_created_gists` tracking
- **`dry_run.py`**: Remove `create_gist` implementation
- **`printing.py`**: Remove `create_gist` implementation

### 12. Update `plan-implement.yml` workflow

**File:** `.github/workflows/plan-implement.yml`

Minimal change — the `upload-session` exec command interface stays the same (same options), just the internal mechanism changes. Verify the step name and any output parsing still works.

### 13. Update `learn.md` command documentation

**File:** `.claude/commands/erk/learn.md`

Update references from `gist_url` to `session_branch` in:

- Step 3 session source objects
- Remote session download instructions (`--session-branch` instead of `--gist-url`)

### 14. Update tests

- `tests/unit/cli/commands/exec/scripts/test_upload_session.py` — Replace gist assertions with branch assertions
- `tests/unit/cli/commands/exec/scripts/test_download_remote_session.py` — Replace gist download tests with branch download tests
- `tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py` — Update remote session source handling
- `tests/unit/cli/commands/exec/scripts/test_get_learn_sessions.py` — Update session source assertions
- `tests/shared/github/test_plan_header_extraction.py` — Update schema field tests
- Any gateway tests referencing `create_gist`
- Regenerate exec reference docs: `erk-dev gen-exec-reference-docs`

## Files Changed Summary

### Deleted concepts (no file deletions, just removal of gist code paths)

- `create_gist` from GitHub gateway ABC + all implementations
- `GistCreated`, `GistCreateError` types
- `normalize_gist_url()` function
- `last_session_gist_url`, `last_session_gist_id` metadata fields

### Core modifications

- `src/erk/cli/commands/exec/scripts/upload_session.py` — Branch commit instead of gist
- `src/erk/cli/commands/exec/scripts/download_remote_session.py` — Git fetch instead of urllib
- `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` — Branch download + cleanup
- `src/erk/cli/commands/exec/scripts/get_learn_sessions.py` — session_branch field
- `packages/erk-shared/src/erk_shared/learn/extraction/session_source.py` — session_branch
- `packages/erk-shared/src/erk_shared/learn/extraction/get_learn_sessions_result.py` — session_branch
- `packages/erk-shared/src/erk_shared/sessions/discovery.py` — session_branch
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py` — Field swap
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py` — Extractors
- `packages/erk-shared/src/erk_shared/plan_store/backend.py` — Session discovery
- `packages/erk-shared/src/erk_shared/gateway/github/abc.py` — Remove create_gist
- `packages/erk-shared/src/erk_shared/gateway/github/real.py` — Remove create_gist
- `packages/erk-shared/src/erk_shared/gateway/github/fake.py` — Remove create_gist
- `packages/erk-shared/src/erk_shared/gateway/github/dry_run.py` — Remove create_gist
- `packages/erk-shared/src/erk_shared/gateway/github/printing.py` — Remove create_gist
- `.claude/commands/erk/learn.md` — session_branch references
- `.github/workflows/plan-implement.yml` — Verify step compatibility

## Verification

1. `make fast-ci` — All unit tests pass
2. `erk exec upload-session --session-file <test-file> --session-id test --source remote --plan-id <test-plan>` — Verify branch created and metadata stored
3. `erk exec download-remote-session --session-branch session/<plan-id> --session-id test` — Verify session downloaded from branch
4. `erk exec get-learn-sessions <plan-id>` — Verify `session_branch` appears in remote source
5. Verify no remaining references to `gist_url` in learn pipeline code (grep `gist_url` across `src/erk/` and `packages/erk-shared/`)
6. `erk-dev gen-exec-reference-docs` — Regenerate exec reference docs
