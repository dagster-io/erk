# Fix: Remove duplicate `gt submit` in cmux sync workflow

## Context

When running cmux sync from the TUI, `gt submit --no-interactive` executes twice:

1. `erk pr checkout {pr} --script --sync` already includes `gt submit --no-interactive` as a post-cd command when `--sync` is True (see `checkout_cmd.py:316-318`)
2. The explicit `&& gt submit --no-interactive` appended in `cmux_sync_workspace.py:125` runs it again

## Changes

### 1. `src/erk/cli/commands/exec/scripts/cmux_sync_workspace.py` (line 125)

Remove redundant `&& gt submit --no-interactive`:

```python
# Before:
checkout_cmd = f'source "$(erk pr checkout {pr} --script --sync)" && gt submit --no-interactive'

# After:
checkout_cmd = f'source "$(erk pr checkout {pr} --script --sync)"'
```

### 2. `src/erk/tui/commands/registry.py` (line 93)

Same fix for the display string in `_display_copy_pr_checkout`:

```python
# Before:
return f'source "$(erk pr checkout {pr} --script --sync)" && gt submit --no-interactive'

# After:
return f'source "$(erk pr checkout {pr} --script --sync)"'
```

## Verification

- Run `erk exec cmux-sync-workspace --pr <number>` and confirm `gt submit` only runs once
- Run existing tests for cmux_sync_workspace
