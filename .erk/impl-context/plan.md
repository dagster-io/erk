# Plan: Create `erk exec cmux-sync-workspace` and Fix TUI Command Palette

## Context

The TUI command palette has two problems with the cmux sync entries:
1. **Misplaced ACTION**: The `cmux_sync` ACTION command (⚡) is wedged between COPY commands (📋), instead of being co-located with other PLAN ACTIONs at the top
2. **Display overflow**: Both cmux sync entries display the full shell pipeline (`WS=$(cmux new-workspace --command '...' | awk '{print $2}') && cmux rename-workspace ...`) which overflows the command palette width

The solution: create an `erk exec cmux-sync-workspace` command that wraps the shell pipeline, then update the TUI to use it.

## Changes

### 1. Create exec script: `src/erk/cli/commands/exec/scripts/cmux_sync_workspace.py`

New exec command: `erk exec cmux-sync-workspace --pr <N> [--branch <name>]`

- `--pr` (required int): PR number
- `--branch` (optional str): PR head branch name. If omitted, auto-detect via `gh pr view --json headRefName`
- Runs the cmux pipeline via subprocess:
  1. Build checkout command: `source "$(erk pr checkout {pr} --script --sync)" && gt submit --no-interactive`
  2. Create workspace: `cmux new-workspace --command '{checkout_cmd}'`
  3. Parse workspace name from output
  4. Rename workspace: `cmux rename-workspace --workspace "$WS" "{branch}"`
- Output JSON result: `{"success": true/false, "pr_number": N, "branch": "..."}`
- Follow exec script patterns: `@click.pass_context`, frozen dataclass results, discriminated union errors

### 2. Register in `src/erk/cli/commands/exec/group.py`

Add import and registration for `cmux_sync_workspace`.

### 3. Update `src/erk/tui/commands/registry.py`

**Move cmux_sync ACTION** from line 350 (between COPY commands) up to PLAN ACTIONS section (after `rewrite_remote`, before `# === OBJECTIVE ACTIONS ===`).

**Replace display function** `_display_copy_cmux_sync` with shorter display:
```python
def _display_cmux_sync(ctx: CommandContext) -> str:
    return f"erk exec cmux-sync-workspace --pr {ctx.row.pr_number}"
```

Update both `cmux_sync` and `copy_cmux_sync` command definitions to use the new display function.

### 4. Update `src/erk/tui/app.py` `_cmux_sync_async`

Replace inline shell pipeline construction with exec command invocation:
```python
command=["erk", "exec", "cmux-sync-workspace", "--pr", str(pr_number), "--branch", branch]
```

### 5. Update `src/erk/tui/screens/plan_detail_screen.py`

The detail screen handler for `cmux_sync` calls `self.app._cmux_sync_async()` which is already updated in step 4. No additional changes needed.

### 6. Update tests

- `tests/tui/commands/test_registry.py`: Update display name assertions to expect `erk exec cmux-sync-workspace --pr {N}` instead of the full shell pipeline
- `tests/unit/cli/commands/exec/scripts/test_cmux_sync_workspace.py`: New test file for the exec script using `CliRunner` with subprocess mocking

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/cmux_sync_workspace.py` | **New** - exec script |
| `src/erk/cli/commands/exec/group.py` | Add import + registration |
| `src/erk/tui/commands/registry.py` | Move ACTION, shorten display |
| `src/erk/tui/app.py` | Use exec command in `_cmux_sync_async` |
| `tests/tui/commands/test_registry.py` | Update display assertions |
| `tests/unit/cli/commands/exec/scripts/test_cmux_sync_workspace.py` | **New** - exec tests |

## Verification

1. Run registry tests: `pytest tests/tui/commands/test_registry.py`
2. Run new exec script tests: `pytest tests/unit/cli/commands/exec/scripts/test_cmux_sync_workspace.py`
3. Run `erk exec cmux-sync-workspace --help` to verify CLI registration
4. Run full fast-ci to check for regressions
