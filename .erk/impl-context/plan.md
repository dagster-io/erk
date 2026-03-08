# Plan: Add Objective Link to PR Body

## Context

When a PR is associated with an objective (via plan metadata), the PR body should include a visible link to the objective issue between the summary paragraph and `## Key Changes` heading. Currently, objective info only appears in the plan-header metadata block (hidden in a collapsed section) and is not visible at a glance.

Example desired output:
```
This PR adds agent-friendly JSON output infrastructure...

**Objective #9009:** Agent-Friendly CLI

## Key Changes
- ...
```

## Implementation

### 1. Add `_insert_objective_link()` helper — `src/erk/cli/commands/pr/shared.py`

```python
import re

def _insert_objective_link(body: str, objective_summary: str) -> str:
    """Insert an objective link between summary and Key Changes sections."""
    # Parse "Objective #9009: Agent-Friendly CLI" → number + title
    match = re.match(r"Objective #(\d+): (.+)", objective_summary)
    if match is not None:
        objective_line = f"**Objective #{match.group(1)}:** {match.group(2)}"
    else:
        objective_line = f"**Objective:** {objective_summary}"

    key_changes = "## Key Changes"
    idx = body.find(key_changes)
    if idx != -1:
        return body[:idx] + objective_line + "\n\n" + body[idx:]
    return body + "\n\n" + objective_line
```

### 2. Call it from `assemble_pr_body()` — same file, line ~291

Insert one line early in the function, before the plan details are appended:

```python
pr_body_content = body
if plan_context is not None and plan_context.objective_summary is not None:
    pr_body_content = _insert_objective_link(pr_body_content, plan_context.objective_summary)
if plan_context is not None:
    if plan_header is not None:
        pr_body_content = pr_body_content + build_original_plan_section(plan_context.plan_content)
    ...
```

The current code sets `pr_body_content = body` at line 291, then conditionally appends plan sections. We insert the objective link into `pr_body_content` before the plan section logic.

### 3. Add tests — `tests/unit/cli/commands/pr/test_shared.py`

Add tests to the existing `assemble_pr_body` test section:

1. **`test_objective_link_inserted_before_key_changes`** — body with `## Key Changes`, plan_context with `objective_summary="Objective #9009: Agent-Friendly CLI"` → assert `**Objective #9009:** Agent-Friendly CLI` appears before `## Key Changes`

2. **`test_objective_link_appended_when_no_key_changes`** — body without `## Key Changes` → objective link appended after body

3. **`test_no_objective_link_when_summary_is_none`** — `objective_summary=None` → no `**Objective:**` in output

4. **`test_no_objective_link_without_plan_context`** — `plan_context=None` → no `**Objective:**` in output

## Key Files

| File | Change |
|------|--------|
| `src/erk/cli/commands/pr/shared.py` | Add `_insert_objective_link()`, call from `assemble_pr_body()` |
| `tests/unit/cli/commands/pr/test_shared.py` | Add 4 tests for objective link insertion |
| `src/erk/core/plan_context_provider.py` | No changes (reference: `objective_summary` format at line 92) |

## Verification

1. `uv run pytest tests/unit/cli/commands/pr/test_shared.py` — new + existing tests pass
2. `uv run pytest tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py` — existing finalize tests still pass
3. Type check via devrun agent
