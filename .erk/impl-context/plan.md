# Fix: WARNING comment accumulation on metadata block updates

## Context

Each time a metadata block is updated via `replace_metadata_block_in_body()`, an extra `<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->` comment accumulates. This is because:

1. `render_metadata_block()` outputs the WARNING line **before** the `<!-- erk:metadata-block:{key} -->` opening marker
2. `replace_metadata_block_in_body()` regex only matches from the opening marker to the closing marker
3. The old WARNING line is left orphaned, and the new rendered block adds another one

After N updates, there are N warning lines stacked up before the metadata block.

## Fix

**Single file change:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`

### Change 1: Update `replace_metadata_block_in_body()` regex (line 660)

Extend the regex pattern to optionally consume any preceding WARNING comments before the opening marker. This way, on replacement, the old warning(s) are consumed and the new rendered block provides exactly one.

```python
# Before:
pattern = (
    rf"<!-- erk:metadata-block:{escaped_key} -->"
    rf"(.+?)"
    rf"<!-- /erk:metadata-block(?::{escaped_key})? -->"
)

# After:
pattern = (
    rf"(?:<!-- WARNING: Machine-generated\. Manual edits may break erk tooling\. -->\n)*"
    rf"<!-- erk:metadata-block:{escaped_key} -->"
    rf"(.+?)"
    rf"<!-- /erk:metadata-block(?::{escaped_key})? -->"
)
```

### Change 2: Add test for warning accumulation

**File:** `tests/unit/gateways/github/metadata_blocks/test_block_replacement.py`

Add a test that verifies repeated replacements don't accumulate warnings:

```python
def test_replace_metadata_block_does_not_accumulate_warnings() -> None:
    """Test that replacing a block with WARNING prefix doesn't leave orphaned warnings."""
    body = (
        "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->\n"
        "<!-- erk:metadata-block:plan-header -->\n"
        "<details>\n"
        "<summary>plan-header</summary>\n"
        "old content\n"
        "</details>\n"
        "<!-- /erk:metadata-block:plan-header -->"
    )

    new_block = (
        "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->\n"
        "<!-- erk:metadata-block:plan-header -->\n"
        "<details>\n"
        "<summary>plan-header</summary>\n"
        "new content\n"
        "</details>\n"
        "<!-- /erk:metadata-block:plan-header -->"
    )

    result = replace_metadata_block_in_body(body, "plan-header", new_block)
    assert result.count("WARNING: Machine-generated") == 1
```

Also add a test that applies multiple sequential replacements to verify no accumulation:

```python
def test_replace_metadata_block_multiple_updates_single_warning() -> None:
    """Test that multiple sequential updates maintain exactly one warning."""
    # ... apply replace_metadata_block_in_body 3 times in sequence
    # assert exactly 1 WARNING in final result
```

## Verification

1. Run tests: `pytest tests/unit/gateways/github/metadata_blocks/test_block_replacement.py`
2. Run broader metadata tests: `pytest tests/unit/gateways/github/metadata_blocks/`
