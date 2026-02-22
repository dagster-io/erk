# Objective context gate for plan-save

## Context

PR #7836 was saved without `objective_issue` in its plan-header metadata because the plan wasn't created via `/erk:objective-plan` (which creates the `objective-context.marker`). The exit hook only suggests `--objective-issue` when that marker exists, and `plan-save` has no fallback.

**Root cause**: There is no gate ensuring objective context flows through the plan-save pipeline. The marker-based system works when `/erk:objective-plan` is used, but there's no verification that the marker was created, no fallback in `plan-save` to read the marker directly, and no agent guidance to always use the proper entry point.

## Plan

### Step 1: Add marker fallback in `plan-save`

**File**: `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`

When `--objective-issue` is not provided but `session_id` is available, read the `objective-context.marker` directly:

```python
# After plan extraction/validation (~line 183), before create_plan_issue (~line 199):
if objective_issue is None and effective_session_id is not None:
    marker_value = _read_objective_context_marker(effective_session_id, repo_root)
    if marker_value is not None:
        objective_issue = marker_value
        click.echo(
            f"Auto-linked to objective #{marker_value} from session context",
            err=True,
        )
```

The marker-reading function already exists as `_read_objective_context()` in `exit_plan_mode_hook.py`. Extract the core logic into a shared location (or import `get_scratch_dir` and read inline — it's 4 lines).

**Shared location**: `erk_shared/scratch/session_markers.py` — already holds `get_existing_saved_issue()` and `create_plan_saved_issue_marker()`. Add `read_objective_context_marker(session_id: str, repo_root: Path) -> int | None` there. Update `exit_plan_mode_hook.py` to use it instead of the private `_read_objective_context()`.

### Step 2: Add verification gate in `/erk:objective-plan`

**File**: `.claude/commands/erk/objective-plan.md`

After Step 2 (Task agent returns), add a verification step before Step 3:

```
### Step 2.5: Verify Objective Context Marker

Verify the marker was created by the Task agent:

    erk exec marker read --session-id "${CLAUDE_SESSION_ID}" objective-context

If this returns a value matching the objective issue number, proceed.
If it fails or returns wrong value, STOP and report:
"ERROR: objective-context marker not created. Re-run the marker command manually:
  erk exec marker create --session-id '${CLAUDE_SESSION_ID}' --associated-objective <issue-number> objective-context"
```

### Step 3: Add AGENTS.md instruction

**File**: `AGENTS.md`, in the "CRITICAL: Before Writing Any Code" section (after line 28)

Add:

```
**CRITICAL: When creating a plan for an objective, ALWAYS use `/erk:objective-plan` to ensure proper metadata linking.** Do not manually reference objectives in plan text without using the structured workflow. The objective-context marker created by this command is required for the plan-save pipeline to link the plan to its parent objective.
```

### Step 4: Add tests

**File**: `tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py`

Add tests for the marker fallback:
1. `test_plan_save_auto_links_objective_from_marker` — marker exists, `--objective-issue` not provided → objective_issue populated from marker, plan-header contains it
2. `test_plan_save_explicit_flag_overrides_marker` — both marker and `--objective-issue` provided → flag wins (explicit beats implicit)
3. `test_plan_save_no_marker_no_flag` — no marker, no flag → objective_issue stays None (current behavior)

**File**: `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`

Update any tests affected by extracting `_read_objective_context` to shared location.

### Step 5: Retroactive fix for PR #7836

Use existing commands to fix the data:

```bash
# The objective-context marker won't exist for the old session,
# so we need a direct metadata update. Use the plan backend:
erk exec update-dispatch-info pattern (or gh API) to add objective_issue to #7836

# Update objective roadmap nodes to point to #7836
erk exec update-objective-node 7823 --node 1.1 --plan "#7836"
erk exec update-objective-node 7823 --node 1.2 --plan "#7836"
erk exec update-objective-node 7823 --node 1.3 --plan "#7836"
```

*Note: For the retroactive metadata fix, we may still want a small `update-plan-objective` command, or we can patch via `gh api`. This is a one-time fix.*

## Key Files

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py` | Read objective-context marker as fallback |
| `erk_shared/scratch/session_markers.py` | Add `read_objective_context_marker()` |
| `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` | Use shared marker reader instead of private function |
| `.claude/commands/erk/objective-plan.md` | Add marker verification gate (Step 2.5) |
| `AGENTS.md` | Add instruction about using `/erk:objective-plan` |
| `tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py` | Tests for marker fallback |

## Verification

1. `uv run pytest tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py`
2. `uv run pytest tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`
3. `ruff check` and `ty` on modified files
4. End-to-end: run `/erk:objective-plan`, verify marker created, save plan without `--objective-issue`, confirm auto-linked
