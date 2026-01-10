# Plan: Convert --with-dignified-review and --statusline to Capabilities

## Summary

Remove `--with-dignified-review` and `--statusline` flags from `erk init` command and ensure they're available as capabilities via `erk init capability add`.

## Changes

### 1. Remove CLI Flags from `__init__.py`

**File:** `src/erk/cli/commands/init/__init__.py`

Remove:
- `--statusline` option (lines 24-29)
- `--with-dignified-review` option (lines 36-41)
- Parameters from function signature: `statusline_only`, `with_dignified_review`
- Arguments from `run_init()` call: `statusline_only=...`, `with_dignified_review=...`

### 2. Update `run_init()` in `main.py`

**File:** `src/erk/cli/commands/init/main.py`

Remove:
- `statusline_only` parameter from `run_init()` function signature (line 488)
- `with_dignified_review` parameter from function signature (line 490)
- `--statusline` handling block (lines 562-564)
- `--with-dignified-review` handling block (lines 632-641)

### 3. Create DignifiedReviewCapability

**File:** `src/erk/core/capabilities/dignified_review.py` (new file)

Create a capability class following `ErkImplWorkflowCapability` pattern that:
- Name: `dignified-review`
- Installs:
  - `.claude/skills/dignified-python/` (skill)
  - `.github/workflows/dignified-python-review.yml` (workflow)
  - `.github/prompts/dignified-python-review.md` (prompt)
- `is_installed()`: checks if workflow file exists
- `install()`: copies all three artifact types

### 4. Register in Capability Registry

**File:** `src/erk/core/capabilities/registry.py`

- Add import: `from erk.core.capabilities.dignified_review import DignifiedReviewCapability`
- Add to `_all_capabilities()` tuple: `DignifiedReviewCapability()`

## Verification

1. Run `erk init -h` and verify:
   - `--statusline` flag is gone
   - `--with-dignified-review` flag is gone

2. Run `erk init capability list` and verify:
   - `statusline` appears (already exists)
   - `dignified-review` appears (new)

3. Run `erk init capability check dignified-review` to verify check works

4. Run tests: `make pytest-fast` or equivalent

## Notes

- The `statusline` capability already exists in `src/erk/core/capabilities/statusline.py`
- The new `dignified-review` capability reuses logic from `sync_dignified_review()` in `src/erk/artifacts/sync.py`