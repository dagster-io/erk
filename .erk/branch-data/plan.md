# Plan: Fix Graphite Rendering of Details/Summary Blocks

## Context

Graphite doesn't render `<code>` tags inside `<summary>` elements — it shows "Add section title..." instead of the actual summary text. This affects both the `plan-header` metadata block and the `original-plan` details section in draft PR bodies. Additionally, the `---` separator between the metadata block and content doesn't render as a horizontal rule because it needs an extra blank line after the preceding `</details>` HTML block.

## Changes

### 1. Remove `<code>` from `render_metadata_block`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`

- **Line 81:** Change `<summary><code>{block.key}</code></summary>` → `<summary>{block.key}</summary>`
- **Line 531:** Update `parse_metadata_block_body` regex to accept both old (`<code>key</code>`) and new (plain text) formats:
  ```python
  r"<details(?:\s+open)?>\s*<summary>(?:<code>)?[^<]+(?:</code>)?</summary>\s*"
  ```
- Update docstrings at lines 57-66 and 37

### 2. Swap `DETAILS_OPEN` / `_LEGACY_DETAILS_OPEN`

**File:** `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py`

- **Line 87:** `DETAILS_OPEN` becomes the plain-text version (currently `_LEGACY_DETAILS_OPEN`)
- **Line 88:** `_LEGACY_DETAILS_OPEN` becomes the `<code>`-tagged version (currently `DETAILS_OPEN`)
- This preserves backward compat in `extract_plan_content` which tries both

### 3. Add extra line break before separator

**File:** `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py`

- **Line 105** in `build_plan_stage_body`: Add `"\n"` between `metadata_body` and `PLAN_CONTENT_SEPARATOR`:
  ```python
  return metadata_body + "\n" + PLAN_CONTENT_SEPARATOR + DETAILS_OPEN + plan_content + DETAILS_CLOSE
  ```
- `PLAN_CONTENT_SEPARATOR` stays unchanged (`"\n\n---\n\n"`) so `find()` parsing still works for both old and new PRs

### 4. Update test assertion

**File:** `tests/unit/gateways/github/metadata_blocks/test_rendering.py`

- **Line 25:** Change `assert "<summary><code>test-key</code></summary>" in rendered` → `assert "<summary>test-key</summary>" in rendered`

## Verification

1. Run `pytest tests/unit/plan_store/test_draft_pr_lifecycle.py tests/unit/gateways/github/metadata_blocks/test_rendering.py` — verify roundtrip parsing works for both old and new formats
2. Run `ty` and `ruff` on modified files
3. Run `pytest tests/unit/plan_store/ tests/unit/gateways/` — broader test scope to catch regressions
