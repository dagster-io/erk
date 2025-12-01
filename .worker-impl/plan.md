# Fix: Detect "updated remotely" error in gt pr-update workflow

## Problem

When `gt submit` fails with "Branch has been updated remotely", two things go wrong:

1. **Python layer**: `pr_update.py` returns a generic error (no `error_type`)
2. **Agent layer**: The calling agent tries to auto-fix with `gt sync`, which hangs on interactive prompts

The subagent (`gt-update-pr-submitter`) correctly doesn't run `gt sync` - the problem is the outer calling agent attempts recovery.

## Solution

Fix at two layers:

1. **Python layer** - Return structured error with `error_type: "submit_diverged"`
2. **Agent markdown layer** - Add explicit `submit_diverged` response handling to signal this is a terminal error requiring user action

## Files to Modify

1. **`packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/pr_update.py`**
   - Lines 75-78: Replace generic error handling with categorized errors

2. **`packages/dot-agent-kit/tests/unit/kits/gt/test_pr_update.py`**
   - Add test for "updated remotely" error detection

3. **`packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/agents/gt/gt-update-pr-submitter.md`** (canonical)
4. **`.claude/agents/gt/gt-update-pr-submitter.md`** (local copy)
   - Add `submit_diverged` error type to Response Handling section

## Implementation

### 1. Update pr_update.py (lines 75-78)

Replace:

```python
except RuntimeError as e:
    return {"success": False, "error": f"Failed to submit update: {e}"}
```

With:

```python
except RuntimeError as e:
    error_message = str(e)
    error_lower = error_message.lower()

    if "updated remotely" in error_lower or "must sync" in error_lower:
        return {
            "success": False,
            "error_type": "submit_diverged",
            "error": (
                "Branch has diverged from remote. "
                "Run 'gt sync' to synchronize before updating PR."
            ),
            "details": {"stderr": error_message},
        }

    return {"success": False, "error": f"Failed to submit update: {e}"}
```

### 2. Add test to test_pr_update.py

Add test after `test_update_pr_submit_fails`:

```python
def test_update_pr_submit_diverged_detected(self) -> None:
    """Test that 'updated remotely' errors return submit_diverged type."""
    ops = (
        FakeGtKitOps()
        .with_branch("feature-branch", parent="main")
        .with_commits(1)
        .with_submit_failure(
            stderr="Branch feature-branch has been updated remotely. Use gt sync."
        )
    )

    result = execute_update_pr(ops)

    assert result["success"] is False
    assert result["error_type"] == "submit_diverged"
    assert "diverged from remote" in result["error"]
    assert "gt sync" in result["error"]
```

### 3. Update gt-update-pr-submitter.md (both copies)

Add after the "Conflict Error" section in Response Handling:

````markdown
**Diverged Error (requires user action):**

```json
{
  "success": false,
  "error_type": "submit_diverged",
  "error": "Branch has diverged from remote. Run 'gt sync' to synchronize before updating PR."
}
```
````

Display: `Failed: Branch has diverged from remote. User must run 'gt sync' manually to synchronize.`

**IMPORTANT:** This error requires manual user intervention. Do NOT attempt to run `gt sync` or any other recovery command. The user must handle this interactively.

```

```
