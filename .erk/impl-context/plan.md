# Add `erk-remote-setup` to Bundle Capability

## Context

CI failed on `dagster-io/internal` PR #20959 (branch `upgrade-erk-0.8.0`) because the `plan-implement.yml` workflow references `./.github/actions/erk-remote-setup`, but this action was never synced to the internal repo during the erk upgrade.

**Root cause**: The `erk-remote-setup` action is already bundled in the wheel (`pyproject.toml:90`), but `ErkImplWorkflowCapability` doesn't declare it as a managed artifact — so the sync system skips it. All 5 bundled workflows (`plan-implement`, `learn`, `one-shot`, `pr-address`, `pr-fix-conflicts`) depend on this action.

## Changes

### 1. Update `ErkImplWorkflowCapability`

**File**: `src/erk/capabilities/workflows/erk_impl.py`

Add `erk-remote-setup` in 5 locations:

- **Docstring** (line 22-24): Add `.github/actions/erk-remote-setup/` to the "Installs" list
- **`artifacts` property** (line 44-58): Add `CapabilityArtifact(path=".github/actions/erk-remote-setup/", artifact_type="directory")`
- **`managed_artifacts` property** (line 61-67): Add `ManagedArtifact(name="erk-remote-setup", artifact_type="action")`
- **`install` method** (line 96): Add `"erk-remote-setup"` to the `actions` list
- **`uninstall` method** (line 132): Add `"erk-remote-setup"` to the `actions` list

### 2. Update Tests

**File**: `tests/unit/core/test_capabilities.py`

- **`test_erk_impl_workflow_artifacts`** (line 467): Change `len(artifacts) == 3` to `4`, add assertion for `".github/actions/erk-remote-setup/"` in paths
- **`test_workflow_capability_managed_artifacts`** (line 1841): Change `len(managed) == 3` to `4`, add assertion for `("erk-remote-setup", "action")` in names

## Verification

1. Run: `uv run pytest tests/unit/core/test_capabilities.py -k "erk_impl" -v`
2. Run: `uv run ty check src/erk/capabilities/workflows/erk_impl.py`
3. After merging and re-upgrading erk in internal: re-run `erk artifact sync` to confirm `erk-remote-setup` gets synced
