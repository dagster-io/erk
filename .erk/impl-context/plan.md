# Fix: TUI close command silently fails with Graphite URLs

## Context

The "close" command in the TUI's command palette shows a success toast ("Closed PR #9268") but doesn't actually close the PR. This happens because `close_pr` extracts `owner/repo` by parsing the `pr_url`, which only handles `https://github.com/` URLs. When Graphite is enabled, `pr_url` is a Graphite URL (`https://app.graphite.dev/...`), so parsing fails and the method silently returns without closing.

## Root Cause

Two bugs in `RealPrService.close_pr()`:

1. **`_parse_owner_repo_from_url` only handles GitHub URLs** (line 227: `if not url.startswith("https://github.com/"): return None`) — Graphite URLs are silently rejected
2. **Silent failure** — when parsing fails, `close_pr` returns `[]` (line 81-82) instead of raising, so `_close_pr_async` in `workers.py` treats it as success and shows the toast

## Fix

Use `self._location.repo_id` (which has `.owner` and `.repo`) directly in `close_pr` instead of parsing from the URL. The URL is unnecessary since the service already knows the repository.

### File: `packages/erk-shared/src/erk_shared/gateway/pr_service/real.py`

Change `close_pr` (lines 70-90):

```python
def close_pr(self, pr_number: int, pr_url: str) -> list[int]:
    owner = self._location.repo_id.owner
    repo = self._location.repo_id.repo

    self._http_client.patch(
        f"repos/{owner}/{repo}/issues/{pr_number}",
        data={"state": "closed"},
    )

    return []
```

This eliminates the URL parsing entirely. `_parse_owner_repo_from_url` can be removed if no other callers use it (verify first).

## Verification

1. Run existing tests: `pytest tests/ -k "close_pr"`
2. Manual: open `erk dash -i`, select a test plan, run close from command palette — PR should disappear after refresh
3. Verify `_parse_owner_repo_from_url` has no other callers before removing it
