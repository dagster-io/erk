# Plan: Strip "Documentation Plan: " Prefix from Learn Plan Titles

## Problem

Learn plans created by `plan-synthesizer.md` use the format:
```markdown
# Documentation Plan: <title>
```

When this title is extracted via `extract_title_from_plan()`, the "Documentation Plan: " prefix is NOT stripped because it's not in `_PLAN_PREFIXES`. The result is redundant GitHub issue titles like:

```
[erk-learn] Documentation Plan: Feature Name
```

The `[erk-learn]` tag already indicates it's a documentation/learn plan, making the prefix redundant.

## Solution

Add "Documentation Plan: " to the `_PLAN_PREFIXES` tuple so it gets stripped during title extraction.

## Files to Modify

### 1. `packages/erk-shared/src/erk_shared/plan_utils.py`

**Line 14**: Add "Documentation Plan: " to `_PLAN_PREFIXES`:

```python
_PLAN_PREFIXES = ("Plan: ", "Implementation Plan: ", "Documentation Plan: ")
```

### 2. `packages/erk-shared/tests/unit/test_plan_utils.py`

Add test after line 147:

```python
def test_extract_title_strips_documentation_plan_prefix() -> None:
    """Test title extraction strips 'Documentation Plan: ' prefix from H1."""
    plan = "# Documentation Plan: Learn Workflow\n\nDetails..."
    assert extract_title_from_plan(plan) == "Learn Workflow"
```

## Verification

1. Run unit tests: `make test-unit` (via devrun agent)
2. Verify the new test passes
3. Verify existing prefix-stripping tests still pass