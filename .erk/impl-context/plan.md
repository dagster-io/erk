# Consolidate dataclass JSON serialization in exec scripts

## Context

`packages/erk-shared/src/erk_shared/agentclick/dataclass_json.py` provides centralized utilities for dataclass-to-JSON serialization (`serialize_to_json_dict`) and JSON emission (`emit_json_success`, `emit_json_error`). However, 27 exec scripts in `src/erk/cli/commands/exec/scripts/` bypass these utilities and hand-roll the same pattern: `click.echo(json.dumps(asdict(result), indent=2))`. This creates 70+ call sites of duplicated serialization logic.

`machine_schema.py` was also identified but already properly delegates to `dataclass_json.py` — its `request_schema()` function serves a fundamentally different purpose (input schema with optional fields, no `success` injection) from `dataclass_result_schema()` (output schema, all required, adds `success: true`). No changes needed there.

## Plan

### Step 1: Add `emit_json_result` to `dataclass_json.py`

**File:** `packages/erk-shared/src/erk_shared/agentclick/dataclass_json.py`

Add a new function that handles the most common exec script pattern (stdout, indent=2):

```python
def emit_json_result(result: Any) -> None:
    """Emit a serialized dataclass as indented JSON to stdout."""
    import click
    click.echo(json.dumps(serialize_to_json_dict(result), indent=2))
```

This replaces the 3-import, 1-line pattern (`from dataclasses import asdict` + `import json` + `import click` + `click.echo(json.dumps(asdict(result), indent=2))`) with a single import and call.

### Step 2: Migrate 27 exec scripts

For each of the 27 exec scripts, apply this mechanical transformation:

**Before:**
```python
from dataclasses import asdict, dataclass
import json
import click
...
click.echo(json.dumps(asdict(result), indent=2))
```

**After:**
```python
from dataclasses import dataclass
from erk_shared.agentclick.dataclass_json import emit_json_result
...
emit_json_result(result)
```

**Variant handling:**
- **`indent=2` to stdout** (most common): Direct replacement with `emit_json_result(result)`
- **No indent to stdout** (e.g., `get_plan_metadata.py`): Replace `asdict(result)` with `serialize_to_json_dict(result)`, keep `click.echo(json.dumps(...))`
- **`err=True` to stderr** (e.g., `store_tripwire_candidates.py`): Replace `asdict(error)` with `serialize_to_json_dict(error)`, keep `click.echo(..., err=True)`
- Remove `from dataclasses import asdict` when no longer used (keep `dataclass` import)
- Remove `import json` when no longer used

**Files (27):**
- `add_plan_labels.py`, `add_pr_labels_cmd.py`, `ci_update_pr_body.py`, `ci_verify_autofix.py`
- `close_prs.py`, `cmux_checkout_workspace.py`, `detect_trunk_branch.py`, `get_plan_metadata.py`
- `get_pr_for_plan.py`, `get_pr_review_comments.py`, `handle_no_changes.py`, `impl_signal.py`
- `list_sessions.py`, `normalize_tripwire_candidates.py`, `post_or_update_pr_summary.py`
- `post_pr_inline_comment.py`, `post_workflow_started_comment.py`, `pr_sync_commit.py`
- `quick_submit.py`, `resolve_review_thread.py`, `resolve_review_threads.py`
- `store_tripwire_candidates.py`, `track_learn_evaluation.py`, `track_learn_result.py`
- `update_objective_node.py`, `update_plan_header.py`, `validate_claude_credentials.py`

### Step 3: No changes to `machine_schema.py`

`machine_schema.py`'s `request_schema()` already imports and delegates to `python_type_to_json_schema` from `dataclass_json.py`. Its field-iteration logic handles optional/default fields differently from `dataclass_result_schema` — this is intentional, not duplication.

## Verification

1. Run `ruff check` and `ruff format` on modified files
2. Run `ty` for type checking
3. Run `pytest tests/unit/cli/commands/exec/scripts/` for exec script tests
4. Run `pytest tests/` for full test suite to catch import issues
5. Grep for any remaining `from dataclasses import.*asdict` in exec scripts to confirm complete migration
