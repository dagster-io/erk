# Plan: Let uv auto-discover Python version from repo config

## Context

The `erk-remote-setup` action hardcodes `python-version: "3.13"` in its `setup-uv` step. This means customer repos can't control their Python version — they're forced to use whatever erk hardcodes. Instead of adding an erk-specific customization hook, we can remove the `python-version` input entirely and let uv auto-discover from each repo's standard config (`.python-version` file or `requires-python` in `pyproject.toml`).

All 6 erk remote workflows (`plan-implement`, `one-shot`, `pr-address`, `pr-rebase`, `pr-rewrite`, `learn`) use `erk-remote-setup`, so this single change fixes all of them.

## Changes

### 1. Remove `python-version` from `erk-remote-setup`

**File:** `.github/actions/erk-remote-setup/action.yml` (line 32)

Remove the `python-version` line from the `setup-uv` step:

```yaml
# Before
    - uses: astral-sh/setup-uv@v5
      with:
        python-version: "3.13"

# After
    - uses: astral-sh/setup-uv@v5
```

Without `python-version`, `UV_PYTHON` won't be set, and uv will discover the version from:
1. `.python-version` in the repo (erk's is `3.13`)
2. `requires-python` in `pyproject.toml`
3. System Python / auto-download

### 2. Update documentation

**File:** `docs/learned/ci/plan-implement-customization.md`

Update the "Extension Point" section to reflect that Python version is now auto-discovered from repo config via uv, not via the `erk-impl-setup` composite action. Remove the `python-version` output table and example. Document that repos control Python version through `.python-version` or `pyproject.toml`.

### 3. Also remove from worktree's `erk-impl.yml`

**File (worktree):** `.github/workflows/erk-impl.yml` (lines 68-76)

Remove the `erk-impl-setup` conditional step (lines 68-71) and remove `python-version` from the `setup-uv` step (line 76). This file is on the current branch and needs the same treatment.

## Not changed

- `.github/workflows/ci.yml` — intentionally tests across a Python version matrix (`3.11`, `3.12`, `3.13`, `3.14`). This is correct and unrelated.
- `.github/actions/setup-python-uv/action.yml` — uses `actions/setup-python@v5` (different pattern), not `setup-uv`. Separate concern.

## Verification

- Review the diff to confirm only `python-version` lines were removed
- Confirm erk's `.python-version` file contains `3.13` (so erk's own CI behavior won't change)
