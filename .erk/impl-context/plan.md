# Add `--version` option to `reserve-pypi-name` command

## Context

PyPI rejects uploads that reuse filenames from previously deleted packages. The `reserve-pypi-name` command hardcodes version `0.0.1`, so if a name was reserved and then deleted, re-reserving fails. Adding a `--version` option lets the user specify an alternative version (e.g., `0.0.2`).

## Changes

**File:** `packages/erk-dev/src/erk_dev/commands/reserve_pypi_name/command.py`

1. Add `--version` click option with default `"0.0.1"`
2. Thread `version` parameter through to `render_pyproject()` and `render_init_py()` (replacing `PLACEHOLDER_VERSION` usage)
3. Remove the `PLACEHOLDER_VERSION` constant
4. Update dry-run output to show the version being used

## Verification

```
erk-dev reserve-pypi-name --name twerk --version 0.0.2 --dry-run
```
