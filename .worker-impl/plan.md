# Plan: Add `erk exec trigger-async-learn` Command

**Part of Objective #4991, Step 3.2**

## Goal

Create an exec command that triggers the `learn-async.yml` workflow for a given plan issue. This is the CLI frontend for dispatching async learning.

## Context

This command will be used:
1. **By `erk land`** (steps 3.3-3.5) - when user opts to trigger async learn at land time
2. **Manually** - when user wants to trigger learning independently

**Prerequisites:**
- `learn-async.yml` workflow exists (step 3.1, PR #5407 in progress)
- Session artifacts exist (uploaded by erk-impl or step 2.6's upload-session-artifact)

## Design Decisions

1. **Input**: Accept plan issue number as required argument
2. **Validation**: Verify issue is an erk-plan with session data available
3. **Dispatch**: Use `gh workflow run learn-async.yml -f issue_number=<N>`
4. **Update plan header**: Set `learn_status=pending` after successful dispatch
5. **Output**: JSON with success status and workflow run URL

## Implementation

### Create `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`

```python
@click.command(name="trigger-async-learn")
@click.argument("issue_number", type=int)
@click.pass_context
def trigger_async_learn(ctx: click.Context, issue_number: int) -> None:
    """Trigger async learn workflow for a plan issue."""
```

**Steps:**
1. Get repo root and GitHub gateway from context
2. Validate issue exists and has `erk-plan` label
3. Check if session artifact exists (via plan header's `last_remote_impl_run_id` or `last_local_impl_session`)
4. Dispatch workflow: `gh workflow run learn-async.yml -f issue_number=<N>`
5. Update plan header: set `learn_status=pending`
6. Output JSON: `{success: true, issue_number, workflow_triggered: true}`

**Error cases:**
- Issue not found → `{success: false, error: "Issue not found"}`
- Not an erk-plan → `{success: false, error: "Issue is not an erk-plan"}`
- No session data → `{success: false, error: "No session data available for learning"}`
- Workflow dispatch fails → `{success: false, error: "Failed to dispatch workflow"}`

### Register in exec group

Add to `src/erk/cli/commands/exec/group.py`:
```python
from erk.cli.commands.exec.scripts.trigger_async_learn import trigger_async_learn
exec_group.add_command(trigger_async_learn)
```

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` | Create | Main exec command |
| `src/erk/cli/commands/exec/group.py` | Modify | Register command |
| `tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py` | Create | Unit tests |

## Verification

1. **Manual test:**
   ```bash
   erk exec trigger-async-learn 5406
   ```

2. **Expected output:**
   ```json
   {"success": true, "issue_number": 5406, "workflow_triggered": true}
   ```

3. **Verify:**
   - Workflow appears in Actions tab
   - Plan header updated with `learn_status: pending`

## Related Documentation

- `docs/learned/tripwires.md` - exec script patterns
- `src/erk/cli/commands/exec/scripts/AGENTS.md` - dependency injection requirements