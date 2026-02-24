# Plan: Migrate `gh workflow run` and `gh run list` to REST API

## Context

The `gh` CLI's porcelain commands (`gh workflow run`, `gh run list`) silently use GraphQL internally to resolve repo context (e.g., default branch). This consumes the GraphQL rate limit quota (5,000 points/hour), which is shared with erk's intentional GraphQL queries (dash, review threads, batch node lookups). A single `erk plan submit` can burn ~12 GraphQL calls through porcelain commands — all of which have direct REST API equivalents that use a separate 5,000 requests/hour quota.

This migration eliminates GraphQL consumption from 4 porcelain call sites, reserving the GraphQL budget for queries that actually require it.

## Files to Modify

- `packages/erk-shared/src/erk_shared/gateway/github/real.py` — main implementation (4 call sites)
- `tests/integration/test_real_github.py` — integration tests that mock subprocess for `trigger_workflow`

## Changes

### 1. Add `_get_default_branch()` helper

New private method on `RealGitHub` to resolve the default branch via REST:

```python
def _get_default_branch(self, repo_root: Path) -> str:
    cmd = ["gh", "api", "repos/{owner}/{repo}", "--jq", ".default_branch"]
    stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
    return stdout.strip()
```

Used by `_dispatch_workflow_impl` when `ref is None` (all current callers pass `ref=None`).

### 2. Migrate `_dispatch_workflow_impl` (line 293-334)

Replace `gh workflow run` with REST API dispatch.

**Before:** `gh workflow run {workflow} --ref {ref} -f distinct_id=... -f key=val`
**After:** `gh api --method POST repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches --input -`

Pass JSON payload via stdin (`input=` kwarg to `subprocess.run()` via `run_subprocess_with_context`):

```python
ref_value = ref if ref is not None else self._get_default_branch(repo_root)
payload = json.dumps({"ref": ref_value, "inputs": {"distinct_id": distinct_id, **inputs}})

cmd = [
    "gh", "api",
    "--method", "POST",
    f"repos/{{owner}}/{{repo}}/actions/workflows/{workflow}/dispatches",
    "--input", "-",
]
run_subprocess_with_context(
    cmd=cmd,
    operation_context=f"trigger workflow '{workflow}'",
    cwd=repo_root,
    input=payload,
)
```

The dispatch endpoint returns 204 No Content on success (empty stdout, exit code 0).

### 3. Migrate polling in `trigger_workflow` (lines 382-393)

Replace `gh run list --workflow --json --limit 10` with REST API.

**Before:** `gh run list --workflow {w} --json databaseId,status,conclusion,displayTitle --limit 10`
**After:** `gh api repos/{owner}/{repo}/actions/workflows/{workflow}/runs?per_page=10 --jq .workflow_runs`

Field name mapping (porcelain camelCase -> REST snake_case):
| Porcelain | REST API |
|---|---|
| `databaseId` | `id` |
| `displayTitle` | `display_title` |
| `status` | `status` |
| `conclusion` | `conclusion` |

Update all field accesses in the polling loop accordingly:
- `run["databaseId"]` -> `run["id"]`
- `run.get("displayTitle", "")` -> `run.get("display_title", "")`

### 4. Migrate `list_workflow_runs` (lines 558-606)

Replace `gh run list --workflow --json --limit N` with REST API.

**Before:** `gh run list --workflow {w} --json databaseId,...,createdAt --limit {n} [--user {u}]`
**After:** `gh api "repos/{owner}/{repo}/actions/workflows/{workflow}/runs?per_page={n}[&actor={u}]" --jq .workflow_runs`

Field mapping for WorkflowRun construction:
- `run["databaseId"]` -> `run["id"]`
- `run["headBranch"]` -> `run["head_branch"]`
- `run["headSha"]` -> `run["head_sha"]`
- `run.get("displayTitle")` -> `run.get("display_title")`
- `run.get("createdAt")` -> `run.get("created_at")`

Use `execute_gh_command_with_retry` here (consistent with other REST-based list operations).

### 5. Migrate `poll_for_workflow_run` (lines 940-953)

Replace `gh run list --workflow --json --limit 20` with REST API.

**Before:** `gh run list --workflow {w} --json databaseId,...,headBranch --limit 20`
**After:** `gh api "repos/{owner}/{repo}/actions/workflows/{workflow}/runs?per_page=20" --jq .workflow_runs`

Field mapping:
- `run["databaseId"]` -> `run["id"]`
- `run.get("headBranch")` -> `run.get("head_branch")`
- `run.get("createdAt")` -> `run.get("created_at")`
- `run.get("conclusion")` -> (unchanged)
- `run.get("event")` -> (unchanged)

### 6. Update GH-API-AUDIT comments

Update all 4 audit comments to reflect the migration:
- `# GH-API-AUDIT: REST - POST workflows/{id}/dispatches` (already correct label, now actually REST)
- `# GH-API-AUDIT: REST - GET actions/workflows/{id}/runs` (3 locations)

### 7. Update integration tests (`tests/integration/test_real_github.py`)

4 tests mock `subprocess.run` and check specific command patterns / response formats:

1. **`test_trigger_workflow_handles_empty_list_during_polling`** (line 485):
   - Dispatch detection: change from checking `"workflow" in cmd and "run" in cmd` to checking for `actions/workflows` in cmd args
   - Distinct ID extraction: change from parsing `-f distinct_id=xxx` args to parsing JSON from `kwargs.get("input")`
   - Polling response: change from flat JSON array `[{"databaseId": ..., "displayTitle": ...}]` to flat array with snake_case fields `[{"id": ..., "display_title": ...}]` (the `--jq .workflow_runs` already extracts the array)

2. **`test_trigger_workflow_errors_on_invalid_json_structure`** (line 549):
   - Same dispatch detection update
   - Invalid response is still `{"error": "invalid"}` (a dict instead of list) — this test still validates the same check

3. **`test_trigger_workflow_timeout_after_max_attempts`** (line 588):
   - Same dispatch detection update
   - Empty response is still `[]` — no change to response format
   - Debug message assertion: update from `"gh run list --workflow"` to `"gh api repos/..."`

4. **`test_trigger_workflow_raises_on_skipped_cancelled_runs`** (line 631):
   - Same dispatch/distinct-ID extraction updates
   - Response field names: `databaseId` -> `id`, `displayTitle` -> `display_title`

### 8. Update debug commands in error message (lines 473-475)

The timeout error message includes debug commands referencing porcelain:
```python
f"  gh run list --workflow {workflow} --limit 10",
f"  gh workflow view {workflow}",
```

Update to REST equivalents:
```python
f'  gh api "repos/{{owner}}/{{repo}}/actions/workflows/{workflow}/runs?per_page=10"',
```

## What Does NOT Change

- **ABC interface** (`abc.py`): Method signatures are implementation-agnostic
- **Fake implementation** (`fake.py`): Doesn't use `gh` CLI
- **Dry-run implementation** (`dry_run.py`): Wraps the ABC, no direct CLI calls
- **Printing wrapper** (`printing.py`): Delegates to wrapped implementation
- **Unit tests using fakes**: All pass through FakeGitHub, unaffected
- **`get_workflow_run`** (line 608): Already uses `gh api` REST

## Verification

1. Run integration tests: `uv run pytest tests/integration/test_real_github.py -k trigger_workflow`
2. Run unit tests that exercise trigger/dispatch: `uv run pytest tests/unit/core/github/test_trigger_workflow.py`
3. Run command tests that use trigger_workflow: `uv run pytest tests/commands/launch/ tests/commands/submit/ tests/commands/plan/test_submit.py`
4. Type check: `uv run ty check packages/erk-shared/src/erk_shared/gateway/github/real.py`
5. Manual smoke test: `erk plan submit <issue>` to verify end-to-end workflow dispatch works
