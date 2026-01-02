# Plan: Complete Current PR + Create Follow-up Issue

## Context

PR review requested moving inline imports to top-level. This created a circular import issue. The proper fix (ErkInstallation gateway with fakes) is too large for this PR.

## Plan for Current PR

### Step 1: Revert bundled_paths.py changes

Delete the new `src/erk/artifacts/bundled_paths.py` file and restore the inline imports in `sync.py`.

### Step 2: Revert test patches

Restore all test patches to use `erk.artifacts.sync.get_bundled_*` or `erk.artifacts.artifact_health.get_bundled_*` as they were before.

### Step 3: Reply to PR review

Explain that eliminating import-based side effects requires a proper ErkInstallation gateway refactor, which will be done in a follow-up PR.

### Step 4: Create GitHub issue for ErkInstallation gateway

Create issue with the full refactor plan (below).

---

## Follow-up Issue: ErkInstallation Gateway

**Goal**: Create a unified gateway for erk installation state, replacing mocks with fakes.

**Scope**:
- ABC: `ErkInstallation` with methods for bundled paths + artifact state
- Real: `RealErkInstallation`
- Fake: `FakeErkInstallation` for testing
- DryRun: `DryRunErkInstallation` for save operations
- Add to ErkContext
- Update ~40 test files to use fake injection

**Files**:
- New: `packages/erk-shared/src/erk_shared/gateway/installation/`
- New: `tests/fakes/installation.py`
- Delete: `src/erk/artifacts/bundled_paths.py`, `src/erk/artifacts/state.py`
- Modify: ErkContext, sync.py, artifact_health.py, staleness.py, ~40 tests