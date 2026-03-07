# Fix: Land learn pipeline should fetch remote sessions from async-learn branch

## Context

When landing a PR that was implemented remotely (via `erk:pr-dispatch`), the land pipeline's auto-learn step fails to find session data. The remote implementation uploads preprocessed session XMLs to an `async-learn/{plan_id}` branch, but `land_learn.py` only checks local disk via `get_readable_sessions()` → `find_session_globally()`. This causes `(not found)` for every session and skips learn plan creation entirely.

The `/erk:learn` skill already handles this correctly via `get_learn_sessions.py` which fetches the manifest from the async-learn branch. The land pipeline needs the same capability.

## Changes

### 1. Add `_fetch_xmls_from_async_learn_branch()` to `land_learn.py`

**File:** `src/erk/cli/commands/land_learn.py`

Add a new function that:
- Takes `git: Git`, `repo_root: Path`, `plan_id: str`
- Checks if `async-learn/{plan_id}` branch exists on remote via `git.branch.branch_exists_on_remote()`
- Fetches the branch via `git.remote.fetch_branch()`
- Reads `.erk/sessions/manifest.json` via `git.commit.read_file_from_ref()`
- Downloads each XML file listed in the manifest
- Returns `dict[str, str]` mapping `{IMPL_CONTEXT_DIR}/sessions/{filename}` to XML content

Reuses the same gateway methods that `fetch_sessions.py` uses (`_fetch_manifest` and `_fetch_file_from_branch`), but inline since they're simple (3-5 lines each) and the private functions can't be imported.

Add `import json` to the imports (already used by the module indirectly via session_schema but not directly imported).

### 2. Add branch fallback in `_create_learn_pr_impl()`

**File:** `src/erk/cli/commands/land_learn.py`, lines ~484-494

After `xml_files = _log_session_discovery(...)` returns empty but `all_session_ids` is non-empty, try the branch fallback before skipping:

```python
if not xml_files and all_session_ids:
    xml_files = _fetch_xmls_from_async_learn_branch(
        ctx.git, repo_root=state.main_repo_root, plan_id=plan_id
    )
    if xml_files:
        user_output(
            click.style("✓", fg="green")
            + f" Fetched {len(xml_files)} file(s) from async-learn/{plan_id}"
        )

if not xml_files:
    # existing skip logic unchanged
```

### 3. Same fallback in `_create_learn_pr_for_merged_branch()`

**File:** `src/erk/cli/commands/land_learn.py`, lines ~85-95

Same pattern as step 2 — add the branch fallback between `_log_session_discovery()` and the skip guard.

### 4. Tests

**File:** `tests/unit/cli/commands/land/test_land_learn.py`

Add tests following existing patterns:

- **`test_fetches_from_async_learn_branch_when_local_not_found`**: Configure `FakeGit` with:
  - `_remote_branches` containing `origin/async-learn/100`
  - `_ref_file_contents` containing manifest JSON and XML file content
  - Verify a learn PR is created using the remote XML content

- **`test_skips_when_async_learn_branch_not_found`**: No remote branch configured → still skips with existing message

- **`test_fetch_xmls_returns_empty_when_no_branch`**: Direct unit test of `_fetch_xmls_from_async_learn_branch` returning `{}`

- **`test_fetch_xmls_returns_xml_content_from_manifest`**: Direct unit test with fake git data, verifying correct dict structure

Use existing `_land_state()`, `_make_pr_details()`, `_make_sessions()` helpers. Configure `FakeGit` with `ref_file_contents` dict for `read_file_from_ref` and `remote_branches` for `branch_exists_on_remote`.

## Key files

- `src/erk/cli/commands/land_learn.py` — main changes
- `tests/unit/cli/commands/land/test_land_learn.py` — tests
- `src/erk/cli/commands/exec/scripts/fetch_sessions.py` — reference implementation (not modified)
- `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/fake.py` — `_ref_file_contents` for testing
- `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/fake.py` — `_remote_branches` for testing

## Verification

1. Run scoped tests: `pytest tests/unit/cli/commands/land/test_land_learn.py`
2. Run type checker on changed file
3. Run linter on changed file
