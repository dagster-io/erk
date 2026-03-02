# Plan: Better error messaging for workflow dispatch failures

## Context

When `erk pr dispatch` fails because the target repository doesn't have the `plan-implement.yml` workflow installed, users see a raw Python traceback (RuntimeError from subprocess) instead of an actionable error message. Per erk's error handling conventions, this should be a `UserFacingCliError` with remediation guidance.

The root cause: `dispatch_cmd.py:268` calls `ctx.github.trigger_workflow()` with no error handling. When the workflow doesn't exist, GitHub returns HTTP 404, `run_subprocess_with_context` wraps it as `RuntimeError`, and it bubbles up as a traceback.

## Implementation

### File: `src/erk/cli/commands/pr/dispatch_cmd.py` (~line 268)

Wrap the `trigger_workflow()` call in a try/except that catches `RuntimeError`, detects the 404/workflow-not-found pattern, and raises `UserFacingCliError` with actionable guidance:

```python
try:
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=DISPATCH_WORKFLOW_NAME,
        inputs=inputs,
        ref=ctx.local_config.dispatch_ref,
    )
except RuntimeError as e:
    error_text = str(e)
    if "404" in error_text or "Not Found" in error_text:
        raise UserFacingCliError(
            f"Workflow '{DISPATCH_WORKFLOW_NAME}' not found in this repository.\n\n"
            "The dispatch workflow must be installed before dispatching plans.\n"
            "Install it with:\n\n"
            f"  erk init capability add erk-impl-workflow"
        ) from e
    raise UserFacingCliError(
        f"Failed to dispatch workflow '{DISPATCH_WORKFLOW_NAME}'.\n\n"
        f"{error_text}"
    ) from e
```

This follows the established pattern from `docs/learned/cli/error-handling-antipatterns.md`:
- Detect known error patterns via keywords at the CLI boundary
- Convert `RuntimeError` to `UserFacingCliError` with `from e` chaining
- Provide actionable remediation command
- Re-raise unexpected errors as `UserFacingCliError` too (not bare RuntimeError) since all `trigger_workflow` failures are user-triggerable

### No other files modified

The `UserFacingCliError` import already exists at line 20 of `dispatch_cmd.py`. The `DISPATCH_WORKFLOW_NAME` constant is already imported at line 16.

## Verification

1. Run `make fast-ci` to verify no regressions
2. Manually test by running `erk pr dispatch` against a repo without the workflow — should see clean `Error: Workflow 'plan-implement.yml' not found...` instead of a traceback
