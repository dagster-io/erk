# Fix workflow-started metadata block rendering

## Context

The `post_workflow_started_comment.py` exec script builds its metadata block with a hardcoded string template instead of using the standard `create_workflow_started_block()` + `render_metadata_block()` API. This causes parse failures during `erk land` because the parser expects a `<details>` structure inside the metadata block markers, but the script puts the `<details>` *around* the markers instead.

The error: `Failed to parse metadata block 'workflow-started': Body does not match expected <details> structure`

## Changes

### 1. Fix `_build_workflow_started_comment()` in `post_workflow_started_comment.py`

**File:** `src/erk/cli/commands/exec/scripts/post_workflow_started_comment.py`

- Import `create_workflow_started_block` and `render_metadata_block` from `erk_shared.gateway.github.metadata.core`
- Replace the hardcoded template with calls to the proper API:
  - Use `create_workflow_started_block()` to create the block (uses `plan_number` not `plan_id`)
  - Use `render_metadata_block()` to render it
- Use `render_erk_issue_event()` for the full comment structure (title + metadata block + description), which already handles the correct layout
- The description section includes the branch, PR link, status, and workflow run link

### 2. Update tests

**File:** `tests/unit/cli/commands/exec/scripts/test_post_workflow_started_comment.py`

- `test_build_comment_contains_all_fields`: Update assertions — `plan_id: 123` becomes `plan_number: 123`, YAML quoting may differ since `yaml.safe_dump` handles it
- `test_build_comment_has_metadata_block`: Keep marker assertions, update field name assertions
- Other comment building tests: Minor assertion tweaks for the new layout
- CLI tests: Should pass with minimal changes (they assert on exit codes and JSON output, not comment format)

## Key files

- `src/erk/cli/commands/exec/scripts/post_workflow_started_comment.py` — primary fix
- `tests/unit/cli/commands/exec/scripts/test_post_workflow_started_comment.py` — test updates
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py` — reference API (read-only)

## Verification

- Run `pytest tests/unit/cli/commands/exec/scripts/test_post_workflow_started_comment.py`
- Run `make fast-ci` to verify no regressions
