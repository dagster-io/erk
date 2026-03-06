# Improve incremental dispatch commit message

## Context

When incremental dispatch commits the plan to a PR branch, the commit message is generic: `"Add incremental plan for PR #N"`. Looking at the commit on GitHub (e.g., PR #8830), it's hard to understand what happened. The user wants the commit to clearly indicate it's an incremental dispatch and include the plan content in the commit body.

## Change

**File:** `src/erk/cli/commands/exec/scripts/incremental_dispatch.py` (line 127-132)

Change the commit message from:
```python
message=f"Add incremental plan for PR #{pr_number}",
```

To a multi-line message with a descriptive subject and the plan content as the body:
```python
message=f"Incremental dispatch for PR #{pr_number}\n\n{plan_content}",
```

This uses the standard git convention of subject line + blank line + body. The plan content is already available as `plan_content` (read on line 96).

**Test:** `tests/unit/cli/commands/exec/scripts/test_incremental_dispatch.py`

No test currently asserts on the commit message content, so no test changes are strictly required. However, we should add an assertion in `test_incremental_dispatch_success` to verify the new message format:
```python
assert "Incremental dispatch" in branch_commits[0].message
assert "My Incremental Plan" in branch_commits[0].message
```

## Verification

Run the incremental dispatch unit tests:
```
uv run pytest tests/unit/cli/commands/exec/scripts/test_incremental_dispatch.py
```
