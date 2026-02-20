# Fix: `extract_metadata_prefix` falsely matches footer separator

## Context

PR #7626's body ended up with two summaries after `erk pr rewrite` — the old summary was preserved and a new one prepended. The root cause: `extract_metadata_prefix()` naively matches the first `\n\n---\n\n` in the body, but that pattern also appears in the footer region (between `**Remotely executed:**` note and checkout instructions). When no metadata block HTML comments are present, the function captures old summary content as the "metadata prefix", which then gets prepended during rewrite.

## Root Cause

`extract_metadata_prefix()` at `draft_pr_lifecycle.py:171-186` uses `pr_body.find(PLAN_CONTENT_SEPARATOR)` where `PLAN_CONTENT_SEPARATOR = "\n\n---\n\n"`. This matches ANY occurrence, not just the metadata-to-content separator. The module docstring (line 82-83) notes this invariant but it breaks when bodies lack a metadata block.

## Changes

### 1. Fix `extract_metadata_prefix` (primary fix)

**File:** `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py` (line 171)

After finding `\n\n---\n\n`, validate that the content before it contains an actual metadata block HTML comment (`<!-- erk:metadata-block:`). If not, return `""`.

```python
def extract_metadata_prefix(pr_body: str) -> str:
    separator_index = pr_body.find(PLAN_CONTENT_SEPARATOR)
    if separator_index == -1:
        return ""
    prefix = pr_body[: separator_index + len(PLAN_CONTENT_SEPARATOR)]
    if "<!-- erk:metadata-block:" not in prefix:
        return ""
    return prefix
```

### 2. Fix `extract_plan_content` backward-compat fallback (same file, line 164)

The backward-compat fallback also uses `PLAN_CONTENT_SEPARATOR` naively. Add the same metadata-block validation. If the separator doesn't follow a metadata block, treat it as if no separator exists (return full body).

```python
# Backward compat: old flat format (metadata + separator + plan content)
separator_index = pr_body.find(PLAN_CONTENT_SEPARATOR)
if separator_index == -1:
    return pr_body
candidate_prefix = pr_body[:separator_index]
if "<!-- erk:metadata-block:" not in candidate_prefix:
    return pr_body
return pr_body[separator_index + len(PLAN_CONTENT_SEPARATOR) :]
```

### 3. Add test for the false-positive case

**File:** `tests/unit/plan_store/test_draft_pr_lifecycle.py`

Add tests verifying both functions return the correct result when `\n\n---\n\n` appears without a metadata block:

```python
def test_extract_metadata_prefix_ignores_footer_separator() -> None:
    """Returns empty when separator exists but no metadata block."""
    body = "## Summary\n\nSome content\n\n**Remotely executed:** [Run #123](url)\n\n---\n\nTo checkout..."
    assert extract_metadata_prefix(body) == ""

def test_extract_plan_content_ignores_footer_separator() -> None:
    """Returns full body when separator exists but no metadata block."""
    body = "## Summary\n\nSome content\n\n**Remotely executed:** [Run #123](url)\n\n---\n\nTo checkout..."
    assert extract_plan_content(body) == body
```

Also update the existing `test_extract_metadata_prefix` and `test_extract_plan_content_backward_compat` to include the metadata marker in their test bodies so they continue to pass:

```python
def test_extract_metadata_prefix() -> None:
    body = "<!-- erk:metadata-block:plan-header -->\nmetadata\n<!-- /erk:metadata-block -->\n\n---\n\nrest of content"
    prefix = extract_metadata_prefix(body)
    assert "<!-- erk:metadata-block:plan-header -->" in prefix
    assert prefix.endswith(PLAN_CONTENT_SEPARATOR)

def test_extract_plan_content_backward_compat() -> None:
    body = "<!-- erk:metadata-block:plan-header -->\nmetadata\n<!-- /erk:metadata-block -->\n\n---\n\nplan content here"
    assert extract_plan_content(body) == "plan content here"
```

## Files to Modify

1. `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py` — fix both functions
2. `tests/unit/plan_store/test_draft_pr_lifecycle.py` — add false-positive tests, update existing tests

## Verification

1. `pytest tests/unit/plan_store/test_draft_pr_lifecycle.py`
2. `pytest tests/unit/plan_store/` (broader plan_store tests)
3. `pytest tests/commands/pr/` (rewrite/submit tests that exercise these functions)
