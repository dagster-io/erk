# Bundle Missing Workflows: one-shot, learn, pr-address, pr-fix-conflicts

## Context

`one-shot.yml` was identified as missing from the `pyproject.toml` force-include bundle, meaning it wouldn't be distributed to external erk users via `erk artifact sync`. Investigation reveals three more workflows with the same problem:

| Workflow | Has Capability? | In pyproject.toml? |
|---|---|---|
| `learn.yml` | ✅ `LearnWorkflowCapability` exists and registered | ❌ Missing |
| `one-shot.yml` | ❌ No capability | ❌ Missing |
| `pr-address.yml` | ❌ No capability | ❌ Missing |
| `pr-fix-conflicts.yml` | ❌ No capability | ❌ Missing |

For external users, `erk launch pr-address`, `erk launch pr-fix-conflicts`, and `erk one-shot` all dispatch to these workflows — if they're not bundled, the dispatch fails silently.

## Changes

### 1. Add `learn.yml` to `pyproject.toml` force-include

The capability already exists; just wire it up:

**`pyproject.toml`** — add after `plan-implement.yml` line (82):
```toml
".github/workflows/learn.yml" = "erk/data/github/workflows/learn.yml"
```

### 2. Create 3 new capability files

Follow the exact pattern from `src/erk/capabilities/workflows/learn.py`.

**`src/erk/capabilities/workflows/one_shot.py`** — `OneShotWorkflowCapability`:
- `name` = `"one-shot-workflow"`
- `managed_artifacts` = `[ManagedArtifact(name="one-shot", artifact_type="workflow")]`
- `install()` copies `bundled_github_dir / "workflows" / "one-shot.yml"` to `repo_root / ".github/workflows/one-shot.yml"`

**`src/erk/capabilities/workflows/pr_address.py`** — `PrAddressWorkflowCapability`:
- `name` = `"pr-address-workflow"`
- `managed_artifacts` = `[ManagedArtifact(name="pr-address", artifact_type="workflow")]`

**`src/erk/capabilities/workflows/pr_fix_conflicts.py`** — `PrFixConflictsWorkflowCapability`:
- `name` = `"pr-fix-conflicts-workflow"`
- `managed_artifacts` = `[ManagedArtifact(name="pr-fix-conflicts", artifact_type="workflow")]`

### 3. Register the 3 new capabilities

**`src/erk/core/capabilities/registry.py`** — add imports and add to `_all_capabilities()` tuple under the `# Workflows` section:
```python
from erk.capabilities.workflows.one_shot import OneShotWorkflowCapability
from erk.capabilities.workflows.pr_address import PrAddressWorkflowCapability
from erk.capabilities.workflows.pr_fix_conflicts import PrFixConflictsWorkflowCapability
```

### 4. Add 3 workflows to `pyproject.toml` force-include

```toml
".github/workflows/one-shot.yml" = "erk/data/github/workflows/one-shot.yml"
".github/workflows/pr-address.yml" = "erk/data/github/workflows/pr-address.yml"
".github/workflows/pr-fix-conflicts.yml" = "erk/data/github/workflows/pr-fix-conflicts.yml"
```

## Critical Files

- `pyproject.toml` lines 81–91 — force-include section
- `src/erk/capabilities/workflows/learn.py` — pattern to follow for new capability files
- `src/erk/core/capabilities/registry.py` — capability registration

## No New Actions Needed

All 4 missing workflows reference `./.github/actions/erk-remote-setup` which is already bundled. `one-shot.yml` also calls `plan-implement.yml` which is also already bundled.

## Verification

Run `uv run pytest tests/artifacts/` — the existing `test_forced_include_paths_exist` test will confirm all `pyproject.toml` sources exist. No new tests are required since the existing test guards this invariant.

To do a manual end-to-end check: in a fresh external project run `erk capability install one-shot-workflow` and verify `one-shot.yml` appears at `.github/workflows/one-shot.yml`.
