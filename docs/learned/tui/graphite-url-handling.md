---
title: TUI Graphite URL Handling
read_when:
  - "implementing TUI commands that operate on PRs by URL"
  - "debugging close failures with Graphite-managed PRs"
  - "understanding why URL parsing was removed from close_pr()"
tripwires:
  - action: "parsing owner/repo from a PR URL in close_pr() or similar methods"
    warning: "URL parsing fails for Graphite URLs (different format). Use self._location.repo_id.owner and self._location.repo_id.repo instead. The structured data is always available and format-independent."
  - action: "implementing _parse_owner_repo_from_url() or similar URL parsing helpers"
    warning: "This helper was removed because URLs can come from multiple providers (GitHub, Graphite) with different formats. Use repo_id from the location context instead."
---

# TUI Graphite URL Handling

## Problem

The TUI close command failed with Graphite-managed PRs because Graphite uses a different URL format than GitHub. A helper `_parse_owner_repo_from_url()` was extracting owner/repo from PR URLs by string parsing, which broke when the URL came from Graphite.

## Solution

Use `self._location.repo_id` (structured data) instead of URL string parsing. The repository context is always available and is format-independent.

## Implementation

`close_pr()` in `packages/erk-shared/src/erk_shared/gateway/pr_service/real.py:70-88`:

```python
def close_pr(self, pr_number: int, pr_url: str) -> list[int]:
    # pr_url is kept for interface consistency but NOT used for extraction
    owner = self._location.repo_id.owner
    repo = self._location.repo_id.repo

    self._http_client.patch(
        f"repos/{owner}/{repo}/issues/{pr_number}",
        data={"state": "closed"},
    )
    return []
```

Note: `pr_url` parameter is retained for interface consistency but marked as unused.

## Pattern: Prefer Repository Context over URL Parsing

When you need owner/repo in a service method:

- **Use**: `self._location.repo_id.owner` / `self._location.repo_id.repo`
- **Avoid**: Parsing `pr_url` or any other URL string

URL formats vary across providers (GitHub, Graphite) and may change. Structured `repo_id` is the canonical source.

## Related Documentation

- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) — 4-place gateway pattern
