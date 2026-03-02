# Make All Workflow Capabilities Auto-Install

## Context

The `erk workflow smoke-test` command in dagster-compass fails with a 404 because `one-shot.yml` was never installed — workflow capabilities are optional and must be explicitly added via `erk init capability add`. This is a footgun: the smoke test assumes the workflow exists but doesn't verify it. Rather than adding a check, we should make all workflows auto-install since they're core to erk's GitHub integration.

## Changes

Add `required = True` property override to all 5 workflow capability classes:

1. `src/erk/capabilities/workflows/learn.py` — `LearnWorkflowCapability`
2. `src/erk/capabilities/workflows/one_shot.py` — `OneShotWorkflowCapability`
3. `src/erk/capabilities/workflows/pr_address.py` — `PrAddressWorkflowCapability`
4. `src/erk/capabilities/workflows/pr_rebase.py` — `PrRebaseWorkflowCapability`
5. `src/erk/capabilities/workflows/erk_impl.py` — `ErkImplWorkflowCapability`

Each gets:
```python
@property
def required(self) -> bool:
    return True
```

No other code changes needed. The existing system already handles `required=True`:
- `erk init` auto-installs required capabilities
- `_get_bundled_by_type()` always includes required capabilities for syncing/health checks
- `erk init --upgrade` reinstalls all required capabilities

## Verification

- Run `make fast-ci` to confirm tests pass
- Verify `list_required_capabilities()` returns all 5 workflow capabilities
