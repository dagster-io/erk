# Plan: Add External Repo Compatibility Testing to CI

## Problem

Workflows and actions in this repo can accidentally depend on erk-specific structure (like `packages/erk-shared`) but only fail when used in external repos. The recent `dignified-python-review.yml` bug is an example - it worked here but broke in `dagster-io/internal`.

## Solution

Add a CI job that simulates an external repo context by removing erk-specific directories, then validates that external-facing workflows still function correctly.

## Implementation

### Phase 1: Create External Compatibility Test Job

**File:** `.github/workflows/ci.yml`

Add a new job that:
1. Checks out the repo
2. Removes `packages/` directory to simulate external repo
3. Runs `setup-claude-erk` action to verify it falls back to PyPI correctly
4. Validates the action succeeds without erk-specific paths

```yaml
external-compat:
  name: External Repo Compatibility
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Install uv
      uses: astral-sh/setup-uv@v5

    - name: Simulate external repo (remove erk-specific dirs)
      run: rm -rf packages/

    - name: Test setup-claude-erk action
      uses: ./.github/actions/setup-claude-erk

    - name: Verify erk installed correctly
      run: erk --version
```

### Phase 2: Document External-Facing Artifacts

Add a comment header to external-facing workflows/actions identifying them as such:

```yaml
# EXTERNAL-COMPATIBLE: This workflow is designed to work in repos outside erk.
# Changes must be tested by the external-compat CI job.
```

Files to mark:
- `.github/actions/setup-claude-erk/action.yml`
- `.github/actions/setup-claude-code/action.yml`
- `.github/workflows/erk-impl.yml`
- `.github/workflows/dignified-python-review.yml`

## Files to Modify

1. `.github/workflows/ci.yml` - Add `external-compat` job
2. `.github/actions/setup-claude-erk/action.yml` - Add header comment
3. `.github/actions/setup-claude-code/action.yml` - Add header comment
4. `.github/workflows/erk-impl.yml` - Add header comment
5. `.github/workflows/dignified-python-review.yml` - Add header comment

## Verification

1. Run CI on the PR - the new `external-compat` job should pass
2. Test failure detection: temporarily break setup-claude-erk to use hardcoded path, verify the job fails
3. After merge, any future changes to external-facing artifacts will be validated automatically

## Alternative Considered

Could also add a linting rule to scan for `packages/` paths, but that's more brittle and doesn't catch runtime issues like missing environment variables or action failures.