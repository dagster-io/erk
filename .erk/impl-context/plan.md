# Fix: Statusline counting stale check runs as failures

## Context

The statusline shows `chks:[✅:21 🚫:9]` even though all checks are green on Graphite. The GitHub REST API endpoint (`/commits/{ref}/check-runs`) returns **all** check runs for a commit, including duplicates from re-runs and superseded workflow attempts. The statusline counts every run without deduplication, so old cancelled/failed runs inflate the fail count.

Graphite deduplicates by check name (showing only the latest). The statusline should do the same.

## Plan

### 1. Add deduplication in `_fetch_check_runs`

**File:** `packages/erk-statusline/src/erk_statusline/statusline.py`

After building `check_contexts` from raw runs (line ~554), deduplicate by `name`, keeping only the latest entry per name. The GitHub API returns runs in reverse chronological order (newest first), so for each name we keep the **first** occurrence.

```python
# Deduplicate by name - GitHub returns multiple runs per check name
# from reruns/superseded workflows. Keep first (most recent) per name.
seen_names: set[str] = set()
deduplicated: list[dict[str, str]] = []
for ctx in check_contexts:
    name = ctx.get("name", "")
    if name not in seen_names:
        seen_names.add(name)
        deduplicated.append(ctx)
check_contexts = deduplicated
```

This is simpler and more robust than timestamp comparison since the API ordering is reliable, and we avoid needing to thread extra fields (`started_at`, `completed_at`) through the dict.

### 2. Add tests for deduplication

**File:** `packages/erk-statusline/tests/test_statusline.py`

Add a test class `TestFetchCheckRunsDeduplication` (or add to existing test structure) that tests `_fetch_check_runs` with mock subprocess output containing duplicate check names. Verify only the latest (first in API response) is kept.

Test cases:
- Two runs with same name, different conclusions (cancelled then success) → keeps success
- Three runs: two dupes + one unique → returns 2 check contexts
- All unique names → no change

## Files to modify

- `packages/erk-statusline/src/erk_statusline/statusline.py` — add dedup logic in `_fetch_check_runs`
- `packages/erk-statusline/tests/test_statusline.py` — add dedup tests

## Verification

1. Run statusline unit tests via devrun agent
2. Manually verify with `gh api repos/dagster-io/erk/commits/plnd/add-ref-current-dispatch-03-02-0737/check-runs | jq '.check_runs | length'` vs `jq '[.check_runs[].name] | unique | length'` to confirm duplicates exist
