# Plan: Add `create_issue` Method to BeadsGateway

## Goal

Add a `create_issue` method to the BeadsGateway ABC so that end-to-end tests can use the gateway abstraction instead of direct subprocess calls.

## Files to Modify

| File | Action |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/beads/abc.py` | Add abstract method |
| `packages/erk-shared/src/erk_shared/gateway/beads/real.py` | Implement with `bd create` |
| `packages/erk-shared/src/erk_shared/gateway/beads/fake.py` | Implement in-memory |
| `packages/erk-shared/src/erk_shared/gateway/beads/dry_run.py` | Add no-op implementation |
| `packages/erk-shared/src/erk_shared/gateway/beads/printing.py` | Add print-then-delegate |
| `tests/shared/gateway/beads/test_fake_beads_gateway.py` | Add unit tests for fake |
| `tests/integration/test_real_beads.py` | Update to use gateway method |

## Method Signature

```python
@abstractmethod
def create_issue(
    self,
    *,
    title: str,
    labels: list[str] | None,
    description: str | None,
) -> BeadsIssue:
    """Create a new issue.

    Args:
        title: Issue title (required)
        labels: Labels to apply (optional)
        description: Issue body content (optional)

    Returns:
        The created BeadsIssue with generated ID and timestamps
    """
    ...
```

## Implementation Details

### 1. abc.py
Add the abstract method signature above.

### 2. real.py
Run `bd create <title> [--label X] [--description Y] --json` and parse the returned issue.

Pattern follows existing LBYL style with `check=False` + returncode check.

### 3. fake.py
- Generate fake ID: `f"bd-{uuid.uuid4().hex[:8]}"`
- Use injected Time for timestamps
- Append to `self._issues` list
- Return the created BeadsIssue

Requires adding `Time` dependency to FakeBeadsGateway constructor.

### 4. dry_run.py
No-op: Return a placeholder BeadsIssue without executing anything.

### 5. printing.py
Print the action, then delegate to wrapped implementation.

### 6. Tests

**Unit tests** (test_fake_beads_gateway.py):
- `test_create_issue_basic` - Creates issue with title only
- `test_create_issue_with_labels` - Labels applied correctly
- `test_create_issue_with_description` - Description stored
- `test_create_issue_generates_unique_ids` - Each call gets unique ID
- `test_create_issue_appears_in_list` - Created issue found by list_issues

**Integration tests** (test_real_beads.py):
- Update existing tests to use `gateway.create_issue()` instead of the `create_beads_issue()` helper function
- Add `test_create_issue_returns_valid_beads_issue` - Verify created issue has all fields

## Verification

1. Run unit tests: `uv run pytest tests/shared/gateway/beads/ -v`
2. Run integration tests: `uv run pytest tests/integration/test_real_beads.py -v` (skipped if bd not installed)
3. Run fast-ci: `make fast-ci`