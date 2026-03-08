# Remove `shell_integration` config and rename `output_for_shell_integration()`

## Context

The `shell_integration` global config boolean is dead code — it's stored/serialized but never read to gate behavior. The `--script` flag on CLI commands controls shell integration behavior, not this config. Removing it to reduce confusion and clean up the config surface.

Additionally, renaming `ScriptResult.output_for_shell_integration()` → `output_for_script_handler()` to avoid naming confusion with the removed config.

## Part 1: Remove `shell_integration` config field

### Config infrastructure
1. **`packages/erk-shared/src/erk_shared/context/types.py`** — Remove `shell_integration: bool = False` from `GlobalConfig` dataclass (~line 239), and from the test helper factory function (~lines 253, 266)
2. **`packages/erk-shared/src/erk_shared/config/schema.py`** — Remove `shell_integration` field from `GlobalConfigSchema` (~lines 110-113)
3. **`packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py`** — Remove read (~line 81) and write (~line 141) of `shell_integration`
4. **`packages/erk-shared/tests/unit/config/test_schema.py`** — Remove from expected fields (~line 32) and overridable keys assertion (~line 144)

### Documentation
5. **`src/erk/cli/commands/branch/checkout_cmd.py:431-432`** — Remove docstring line "Enable shell integration for automatic navigation: erk config set shell_integration true"
6. **`docs/ref/configuration.md`** — Remove shell_integration row and example
7. **`docs/learned/configuration/config-layers.md:35`** — Remove shell_integration line
8. **`docs/learned/glossary.md:315`** — Remove shell_integration example line
9. **`docs/learned/architecture/globalconfig-field-addition.md:73`** — Remove shell_integration from field list

## Part 2: Rename `output_for_shell_integration()` → `output_for_script_handler()`

Use `/rename-swarm` to perform this mechanical rename across all files. The rename targets:

- **Method name**: `output_for_shell_integration` → `output_for_script_handler`
- **Definition**: `packages/erk-shared/src/erk_shared/core/script_writer.py` (~lines 31-75, including docstring and error messages)
- **Call sites** (8 files in `src/erk/cli/commands/`): `checkout_helpers.py`, `navigation_helpers.py`, `implement_shared.py`, `wt/create_cmd.py`, `branch/checkout_cmd.py`, `branch/create_cmd.py`, `stack/consolidate_cmd.py`
- **Tests**: `tests/core/test_script_result_output.py`, `tests/commands/test_create.py`, `tests/commands/test_wt_checkout.py` (rename in test names and calls)

## Verification

1. Run `ruff check` and `ty` for lint/type errors
2. Run `pytest tests/core/test_script_result_output.py tests/commands/test_create.py tests/commands/test_wt_checkout.py packages/erk-shared/tests/unit/config/test_schema.py` for affected tests
3. Grep for any remaining `shell_integration` references (should be zero outside of git history)
