# Plan: Add `lifecycle` field to learned doc frontmatter schema

**Part of Objective #8762, Node 1.1**

## Context

Erk's learned docs currently have no lifecycle tracking. A doc created 6 months ago looks identical to one created yesterday. To support the knowledge promotion pipeline (learned docs → skills), we need frontmatter metadata that tracks where a doc is in its lifecycle: raw (fresh from session extraction), staged (reviewed, accurate), or promoted (absorbed into a skill).

This is the foundation node — Phase 2 (the promotion command and pipeline integration) depends on this metadata existing.

## Changes

### 1. Add `Lifecycle` type and fields to `AgentDocFrontmatter`

**File:** `src/erk/agent_docs/models.py`

- Add `Lifecycle = Literal["raw", "staged", "promoted"]`
- Add two optional fields to `AgentDocFrontmatter`:
  - `lifecycle: Lifecycle | None` — defaults to None (treated as "raw" by consumers)
  - `promoted_to: str | None` — skill name, only valid when lifecycle is "promoted"

### 2. Add validation for the new fields

**File:** `src/erk/agent_docs/operations.py` (in `validate_agent_doc_frontmatter`)

- Validate `lifecycle`: if present, must be one of "raw", "staged", "promoted"
- Validate `promoted_to`: if present, must be a non-empty string
- Cross-validate: if `lifecycle` is "promoted", `promoted_to` must be present
- Cross-validate: if `promoted_to` is present, `lifecycle` must be "promoted"

### 3. Filter promoted docs from index generation

**File:** `src/erk/agent_docs/operations.py` (in `collect_valid_docs`)

- When building category/uncategorized doc lists, skip docs with `lifecycle: promoted`
- These docs should not appear in `index.md` or category index files (their content is now in a skill)
- Their tripwires should still be collected (tripwire retargeting is a separate node)

### 4. Add tests

**File:** `tests/unit/agent_docs/test_validate_frontmatter.py`

- `test_lifecycle_accepts_raw` — lifecycle: "raw" is valid
- `test_lifecycle_accepts_staged` — lifecycle: "staged" is valid
- `test_lifecycle_accepts_promoted_with_promoted_to` — lifecycle: "promoted" + promoted_to: "fake-driven-testing" is valid
- `test_lifecycle_rejects_invalid_value` — lifecycle: "unknown" produces error
- `test_lifecycle_rejects_non_string` — lifecycle: 42 produces error
- `test_promoted_to_requires_lifecycle_promoted` — promoted_to without lifecycle: "promoted" produces error
- `test_lifecycle_promoted_requires_promoted_to` — lifecycle: "promoted" without promoted_to produces error
- `test_promoted_to_rejects_empty_string` — promoted_to: "" produces error
- `test_lifecycle_none_by_default` — omitting lifecycle field results in None

**File:** `tests/unit/agent_docs/test_sync_operations.py` (new or extend existing)

- `test_promoted_docs_excluded_from_index` — docs with lifecycle: "promoted" don't appear in generated index
- `test_promoted_docs_tripwires_still_collected` — tripwires from promoted docs are still included

### 5. Update `erk docs validate` output

**File:** `src/erk/agent_docs/operations.py`

No changes needed — the existing validation pipeline will automatically pick up the new field validation since it flows through `validate_agent_doc_frontmatter`.

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/agent_docs/models.py` | Add `Lifecycle` type, add fields to `AgentDocFrontmatter` |
| `src/erk/agent_docs/operations.py` | Add validation logic, filter promoted docs from `collect_valid_docs` |
| `tests/unit/agent_docs/test_validate_frontmatter.py` | Add lifecycle/promoted_to validation tests |
| `tests/unit/agent_docs/test_sync_operations.py` | Add promoted doc filtering tests (new file if needed) |

## Existing Code to Reuse

- `AuditResult = Literal["clean", "edited"]` pattern in `models.py:11` — same pattern for `Lifecycle`
- `validate_agent_doc_frontmatter` in `operations.py:188` — extend with same validation style as `audit_result`
- `collect_valid_docs` in `operations.py:538` — add filter at line 564 after validation
- `get_args(AuditResult)` pattern in `operations.py:249` — reuse for `Lifecycle` validation

## Verification

1. Run `pytest tests/unit/agent_docs/` — all new and existing tests pass
2. Run `erk docs validate` — existing docs still validate (new fields are optional)
3. Run `erk docs sync --check` — sync still works, no regressions
4. Manually add `lifecycle: promoted` + `promoted_to: fake-driven-testing` to one test doc, run `erk docs sync`, verify it's excluded from index
