# Fix discover-reviews for large PRs

## Problem

The `discover-reviews` command fails on PRs with 300+ changed files because it uses `gh pr diff --name-only`, which hits GitHub's API limit:

```
HTTP 406: Sorry, the diff exceeded the maximum number of files (300)
```

## Solution

Replace `gh pr diff --name-only` with the paginated GitHub REST API:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/files --paginate -q '.[].filename'
```

This handles any number of files by paginating through results.

## Files to Modify

1. `src/erk/cli/commands/exec/scripts/discover_reviews.py` - Update `_get_pr_changed_files()` function

## Implementation

Update lines 64-79 in `discover_reviews.py`:

```python
def _get_pr_changed_files(pr_number: int) -> list[str]:
    """Get list of files changed in a PR.

    Uses GitHub REST API with pagination to handle large PRs.

    Args:
        pr_number: PR number to query.

    Returns:
        List of file paths changed in the PR.
    """
    result = run_subprocess_with_context(
        cmd=[
            "gh", "api",
            f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/files",
            "--paginate",
            "-q", ".[].filename",
        ],
        operation_context=f"get changed files for PR #{pr_number}",
    )
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
```

## Verification

1. Run the command locally against PR 6111:
   ```bash
   uv run erk exec discover-reviews --pr-number 6111 --reviews-dir .github/reviews
   ```
   Should return `"success": true` instead of the 406 error.

2. Run existing tests:
   ```bash
   make test-unit -- tests/unit/cli/commands/exec/scripts/test_discover_reviews.py
   ```