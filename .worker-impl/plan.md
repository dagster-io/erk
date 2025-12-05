# Plan: Add Branch Name Parsing as Fallback for Issue Number

## Summary

Enhance the issue number resolution logic in PR submission to support extracting issue numbers from branch names as a fallback when `.impl/issue.json` doesn't exist. Both preflight and finalize phases will share the same resolution logic.

## Background

Branch naming convention: `{issue_number}-{slug}-{MM-DD-HHMM}` (e.g., `1747-unify-worker-impl-11-30-1640`)

Current behavior:
- Both `preflight.py` and `finalize.py` only read issue_number from `.impl/issue.json`
- If file doesn't exist, issue_number is None and "Closes #N" is not added to footer

## Implementation

### 1. Add Branch Name Parsing Function

**File:** `packages/erk-shared/src/erk_shared/naming.py`

Add a new pure function:

```python
def parse_issue_number_from_branch(branch_name: str) -> int | None:
    """Extract issue number from branch name if present.

    Branch naming convention: {issue_number}-{slug}-{MM-DD-HHMM}
    Examples:
        "1747-unify-worker-impl-11-30-1640" -> 1747
        "1751-create-submitservice-11-30-1653" -> 1751
        "feature-branch" -> None (no leading number)
        "master" -> None

    Args:
        branch_name: Git branch name

    Returns:
        Issue number as int, or None if branch doesn't start with a number
    """
    match = re.match(r"^(\d+)-", branch_name)
    if match:
        return int(match.group(1))
    return None
```

### 2. Add Shared Resolution Function

**File:** `packages/erk-shared/src/erk_shared/impl_folder.py`

Add a shared function that both workflows can use:

```python
from erk_shared.naming import parse_issue_number_from_branch

def resolve_issue_number(impl_dir: Path, branch_name: str | None) -> int | None:
    """Resolve issue number from available sources.

    Resolution priority:
    1. .impl/issue.json (explicit issue reference)
    2. Branch name parsing (convention: {issue_number}-{slug}-{date})

    Args:
        impl_dir: Path to .impl/ directory
        branch_name: Current git branch name (or None)

    Returns:
        Issue number if found from any source, None otherwise
    """
    # Priority 1: Try .impl/issue.json
    if has_issue_reference(impl_dir):
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            return issue_ref.issue_number

    # Priority 2: Parse from branch name
    if branch_name is not None:
        return parse_issue_number_from_branch(branch_name)

    return None
```

### 3. Update Preflight Phase

**File:** `packages/erk-shared/src/erk_shared/integrations/gt/operations/preflight.py`

Replace lines 414-420:

```python
from erk_shared.impl_folder import resolve_issue_number

# Get issue reference using shared resolution
impl_dir = cwd / ".impl"
branch_name = ops.git.get_current_branch(cwd) or current_branch
issue_number = resolve_issue_number(impl_dir, branch_name)
```

### 4. Update Finalize Phase

**File:** `packages/erk-shared/src/erk_shared/integrations/gt/operations/finalize.py`

Replace lines 96-102:

```python
from erk_shared.impl_folder import resolve_issue_number

# Get issue number using shared resolution
impl_dir = cwd / ".impl"
branch_name = ops.git.get_current_branch(cwd)
issue_number = resolve_issue_number(impl_dir, branch_name)
```

### 5. Add Tests

**File:** `packages/erk-shared/tests/unit/test_naming.py`

```python
def test_parse_issue_number_from_branch_with_number() -> None:
    assert parse_issue_number_from_branch("1747-unify-worker-impl-11-30-1640") == 1747
    assert parse_issue_number_from_branch("1751-create-submitservice-11-30-1653") == 1751
    assert parse_issue_number_from_branch("42-feature") == 42

def test_parse_issue_number_from_branch_without_number() -> None:
    assert parse_issue_number_from_branch("feature-branch") is None
    assert parse_issue_number_from_branch("master") is None
    assert parse_issue_number_from_branch("main") is None
    assert parse_issue_number_from_branch("improve-nudges") is None
```

**File:** `packages/erk-shared/tests/unit/test_impl_folder.py` (add to existing)

```python
def test_resolve_issue_number_from_impl_folder(tmp_path: Path) -> None:
    """Test issue resolution prefers .impl/issue.json."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    save_issue_reference(impl_dir, 123, "https://github.com/owner/repo/issues/123")

    # Should use .impl/issue.json even if branch has issue number
    assert resolve_issue_number(impl_dir, "456-feature-branch") == 123

def test_resolve_issue_number_from_branch_name(tmp_path: Path) -> None:
    """Test fallback to branch name when no .impl/issue.json."""
    impl_dir = tmp_path / ".impl"  # doesn't exist

    assert resolve_issue_number(impl_dir, "789-feature-12-01-1234") == 789
    assert resolve_issue_number(impl_dir, "feature-branch") is None
    assert resolve_issue_number(impl_dir, None) is None
```

## Files to Modify

1. `packages/erk-shared/src/erk_shared/naming.py` - Add `parse_issue_number_from_branch()`
2. `packages/erk-shared/src/erk_shared/impl_folder.py` - Add `resolve_issue_number()`
3. `packages/erk-shared/src/erk_shared/integrations/gt/operations/preflight.py` - Use shared resolution
4. `packages/erk-shared/src/erk_shared/integrations/gt/operations/finalize.py` - Use shared resolution
5. Tests for both new functions

## Skills to Load

- `dignified-python-313` - For Python code conventions
- `fake-driven-testing` - For test patterns

## Notes

- The regex `^(\d+)-` ensures we only match branches that START with a number followed by hyphen
- This pattern matches the erk branch naming convention exactly
- Branches like `master`, `main`, or `feature-branch` will not match (returns None)
- Resolution priority: `.impl/issue.json` -> branch name parsing -> None