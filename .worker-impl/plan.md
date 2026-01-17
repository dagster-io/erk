# Plan: Fix pr-address Null Thread ID Handling

## Problem

When GraphQL returns threads with null IDs, the agent fails with:
```
Error: Missing option '--thread-id'
```

This happens because:
1. GraphQL can return `null` for thread `id` field (malformed data from GitHub)
2. `real.py` line 1807-1808 defaults to empty string: `id=node.get("id", "")`
3. Agent calls `erk exec resolve-review-thread --thread-id ""` which Click rejects

## Implementation

### Step 1: Filter threads with invalid IDs in `get_pr_review_comments.py`

**File:** `src/erk/cli/commands/exec/scripts/get_pr_review_comments.py`

**Change:** Add validation before JSON output to filter threads with null/empty IDs.

```python
# In the command function, before JSON output (around line 152):
# Filter out threads with invalid IDs (null from GraphQL)
valid_threads = [t for t in threads if t.id]
result_success = ReviewCommentSuccess(
    ...
    threads=[_format_thread_for_json(t) for t in valid_threads],
)
```

This preserves the gateway's raw data for debugging while preventing invalid data from reaching agents.

### Step 2: Add unit test for null thread ID filtering

**File:** `tests/unit/cli/commands/exec/scripts/test_pr_review_comments.py`

**Add test:**
```python
def test_get_pr_review_comments_filters_null_ids(tmp_path: Path) -> None:
    """Test threads with null/empty IDs are filtered out."""
    # Create thread with empty ID (simulates null from GraphQL)
    valid_thread = make_thread("PRRT_valid", "src/foo.py", 10, "Valid comment")

    # Create thread with empty ID using direct construction
    invalid_thread = PRReviewThread(
        id="",  # Empty ID (from null GraphQL response)
        path="src/bar.py",
        line=20,
        is_resolved=False,
        is_outdated=False,
        comments=(PRReviewComment(
            id=1,
            body="Invalid comment",
            author="reviewer",
            path="src/bar.py",
            line=20,
            created_at="2024-01-01T10:00:00Z",
        ),),
    )

    pr_details = make_pr_details(123)

    fake_github = FakeGitHub(
        pr_details={123: pr_details},
        pr_review_threads={123: [valid_thread, invalid_thread]},
    )

    # Invoke command
    # Assert only valid_thread appears in output (1 thread, not 2)
```

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/get_pr_review_comments.py` | Add validation to filter threads with null/empty IDs |
| `tests/unit/cli/commands/exec/scripts/test_pr_review_comments.py` | Add test for null ID filtering |

## Verification

1. Run unit tests:
   ```bash
   uv run pytest tests/unit/cli/commands/exec/scripts/test_pr_review_comments.py -v
   ```

2. Run fast-ci:
   ```bash
   make fast-ci
   ```

## Related Documentation

- Skills: `dignified-python`, `fake-driven-testing`