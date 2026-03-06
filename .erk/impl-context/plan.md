# Rename cmux sync → cmux checkout

## Context

The erk TUI and exec commands use "cmux sync" to name the operation that creates a cmux workspace and checks out a PR. With the new "checkout" vs "teleport" terminology established in erk, this should be renamed to "cmux checkout" since the underlying operation uses `erk pr checkout --script --sync` and has checkout semantics (local-preserving, worktree-creating).

## Changes

### 1. Rename exec script: `cmux-sync-workspace` → `cmux-checkout-workspace`

**File:** `src/erk/cli/commands/exec/scripts/cmux_sync_workspace.py` → rename to `cmux_checkout_workspace.py`

- Rename Click command: `name="cmux-sync-workspace"` → `name="cmux-checkout-workspace"`
- Rename function: `cmux_sync_workspace` → `cmux_checkout_workspace`
- Rename dataclasses: `CmuxSyncSuccess` → `CmuxCheckoutSuccess`, `CmuxSyncError` → `CmuxCheckoutError`
- Update docstrings/comments

### 2. Update exec group registration

**File:** `src/erk/cli/commands/exec/group.py`

- Update import: `from ...cmux_checkout_workspace import cmux_checkout_workspace`
- Update `add_command`: `name="cmux-checkout-workspace"`

### 3. Update TUI command registry

**File:** `src/erk/tui/commands/registry.py`

- Rename IDs: `cmux_sync` → `cmux_checkout`, `copy_cmux_sync` → `copy_cmux_checkout`
- Rename display names/descriptions: "cmux sync" → "cmux checkout"
- Update `_display_cmux_sync` → `_display_cmux_checkout` (outputs `erk exec cmux-checkout-workspace --pr ...`)

### 4. Update TUI palette actions

**File:** `src/erk/tui/actions/palette.py`

- Update all `command_id == "cmux_sync"` → `"cmux_checkout"`
- Update all `command_id == "copy_cmux_sync"` → `"copy_cmux_checkout"`
- Update op_id: `cmux-sync-{pr}` → `cmux-checkout-{pr}`
- Update notification text

### 5. Update TUI workers

**File:** `src/erk/tui/operations/workers.py`

- Rename `_cmux_sync_async` → `_cmux_checkout_async`
- Update command list: `"cmux-sync-workspace"` → `"cmux-checkout-workspace"`

### 6. Update TUI plan detail screen

**File:** `src/erk/tui/screens/plan_detail_screen.py`

- Update `command_id == "copy_cmux_sync"` → `"copy_cmux_checkout"`
- Update `command_id == "cmux_sync"` → `"cmux_checkout"`
- Update op_id and method call references

### 7. Update tests

**File:** `tests/unit/cli/commands/exec/scripts/test_cmux_sync_workspace.py` → rename to `test_cmux_checkout_workspace.py`
- Update import and all references

**File:** `tests/tui/commands/test_registry.py`
- Update all `cmux_sync` → `cmux_checkout` in IDs, assertions, test names

**File:** `tests/tui/app/test_async_operations.py`
- Rename `TestCmuxSyncAsync` → `TestCmuxCheckoutAsync`
- Update method references and command assertions

### 8. Update documentation

**File:** `.claude/skills/erk-exec/reference.md` — update command name and description
**File:** `.claude/skills/cmux/SKILL.md` — update command references
**File:** `docs/learned/integrations/cmux-integration.md` — update command references
**File:** `docs/learned/tui/tui-command-registration.md` — update if it references cmux_sync

## Semantics verification

The current implementation already has checkout semantics — it calls `erk pr checkout {pr} --script --sync` under the hood. The `--sync` flag runs `gt submit` after checkout. No behavioral changes needed.

## Verification

1. Run unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_cmux_checkout_workspace.py`
2. Run TUI registry tests: `pytest tests/tui/commands/test_registry.py`
3. Run TUI async tests: `pytest tests/tui/app/test_async_operations.py`
4. Run full fast-ci to catch any missed references
