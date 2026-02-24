# Add -d and -u Flag Aliases for erk land

## Context

The `erk land` command has `--down` and `--up` flags that control navigation after landing a PR. Currently these flags only have long-form names, while the `--force` flag already has `-f` as a short alias. Adding `-d` for `--down` and `-u` for `--up` improves ergonomics for frequent CLI users.

## Changes

### 1. Add short aliases to Click option decorators

**File:** `src/erk/cli/commands/land_cmd.py`

**Lines ~1864-1875** — Add `-u` and `-d` as the first argument to the respective `@click.option` decorators:

```python
# BEFORE:
@click.option(
    "--up",
    "up_flag",
    is_flag=True,
    help="Navigate to child branch instead of trunk after landing",
)
@click.option(
    "--down",
    "down_flag",
    is_flag=True,
    help="Navigate to trunk after landing (produces source command)",
)

# AFTER:
@click.option(
    "-u",
    "--up",
    "up_flag",
    is_flag=True,
    help="Navigate to child branch instead of trunk after landing",
)
@click.option(
    "-d",
    "--down",
    "down_flag",
    is_flag=True,
    help="Navigate to trunk after landing (produces source command)",
)
```

This follows the existing pattern used elsewhere in the codebase (e.g., `-f`/`--force` on the same command, `-d`/`--delete-current` in `down.py` and `up.py`, `-v`/`--verbose` in `doctor.py`).

### 2. No test changes required

The existing tests invoke land with `--up` and `--down` (long-form flags), which continue to work unchanged. Click's multi-name option support means both `-u`/`--up` and `-d`/`--down` are automatically recognized. No function signatures change since the Click `"up_flag"` and `"down_flag"` parameter names are unchanged.

Relevant test files that use these flags (all will continue to pass as-is):
- `tests/commands/land/test_up_flag.py` — uses `"--up"` in CLI invocations
- `tests/commands/land/test_core.py` — uses `"--down"` and `"--up"` in CLI invocations

### 3. No other files change

The function signature `land(..., up_flag: bool, down_flag: bool, ...)` is unchanged. The Click parameter name (`"up_flag"`, `"down_flag"`) is unchanged. No callers, tests, or documentation reference `--up`/`--down` in a way that would be affected.

## Files NOT Changing

- `tests/` — No test modifications needed; existing tests use long-form flags
- Function signature in `land_cmd.py` — Only the decorator changes, not the function params
- Any other CLI commands — This is scoped only to the `land` command
- `CHANGELOG.md` — Per project rules, never modified directly

## Verification

1. Run `erk land --help` and confirm `-u`/`--up` and `-d`/`--down` appear in help output
2. Run existing tests: `pytest tests/commands/land/ tests/unit/cli/commands/land/` — all should pass unchanged
3. Run type checker and linter to confirm no regressions