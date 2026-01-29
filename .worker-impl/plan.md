# Plan: Add Plan Review PR Detection Logic

**Part of Objective #6201, Step 2.1**

## Goal

Add detection logic to identify if the current PR is a plan review PR, enabling `pr-address` to switch behavior when operating on plan review PRs (handled in later steps 2.2-2.5).

## Background

Plan review PRs use branch pattern: `plan-review-{issue_number}-{MM-DD-HHMM}`
Example: `plan-review-6214-01-15-1430`

Detection needs to:
1. Parse branch name to identify plan review pattern
2. Extract the plan issue number for later use
3. Provide a reusable utility for other commands

## Implementation Approach

Add a new function `extract_plan_review_issue_number()` to the naming module, following the existing `extract_leading_issue_number()` pattern.

### Phase 1: Add Detection Function

**File:** `packages/erk-shared/src/erk_shared/naming.py`

Add function after `extract_leading_issue_number()` (around line 394):

```python
def extract_plan_review_issue_number(branch_name: str) -> int | None:
    """Extract issue number from a plan review branch name.

    Plan review branches follow the pattern: plan-review-{issue_number}-{timestamp}
    Examples: "plan-review-6214-01-15-1430"

    Args:
        branch_name: Branch name to parse

    Returns:
        Issue number if branch matches plan-review-{number}- pattern, else None

    Examples:
        >>> extract_plan_review_issue_number("plan-review-6214-01-15-1430")
        6214
        >>> extract_plan_review_issue_number("plan-review-42-01-28-0930")
        42
        >>> extract_plan_review_issue_number("P2382-convert-erk-create-raw-ext")
        None
        >>> extract_plan_review_issue_number("feature-branch")
        None
    """
    match = re.match(r"^plan-review-(\d+)-", branch_name)
    if match:
        return int(match.group(1))
    return None
```

### Phase 2: Add Tests

**File:** `tests/core/utils/test_naming.py`

Add test function alongside existing `extract_leading_issue_number` tests:

```python
@pytest.mark.parametrize(
    ("branch_name", "expected"),
    [
        # Valid plan review branches
        ("plan-review-6214-01-15-1430", 6214),
        ("plan-review-42-01-28-0930", 42),
        ("plan-review-1-12-31-2359", 1),
        ("plan-review-99999-01-01-0000", 99999),
        # Not plan review branches
        ("P2382-convert-erk-create-raw-ext", None),
        ("2382-convert-erk-create-raw-ext", None),
        ("feature-branch", None),
        ("master", None),
        ("plan-review", None),  # Missing issue number
        ("plan-review-", None),  # Missing issue number
        ("plan-review-abc-01-15-1430", None),  # Non-numeric issue
    ],
)
def test_extract_plan_review_issue_number(branch_name: str, expected: int | None) -> None:
    assert extract_plan_review_issue_number(branch_name) == expected
```

Also add import to the test file's import block.

## Files to Modify

1. `packages/erk-shared/src/erk_shared/naming.py` - Add `extract_plan_review_issue_number()` function
2. `tests/core/utils/test_naming.py` - Add parametrized tests

## Related Documentation

- `dignified-python` skill for LBYL patterns and modern types
- `fake-driven-testing` skill for test patterns

## Verification

```bash
# Run naming tests
uv run pytest tests/core/utils/test_naming.py -v

# Run type checking
ty check packages/erk-shared/src/erk_shared/naming.py

# Verify function is importable
uv run python -c "from erk_shared.naming import extract_plan_review_issue_number; print('OK')"
```

## Future Steps (Not Part of This PR)

Step 2.2+ will use this function in:
- `pr-address` command to detect plan review mode
- `erk exec plan-update-from-feedback` to know which plan issue to update