# Plan: Update TUI Command Palette — Checkout/Teleport Entries

## Context

The TUI command palette (`erk dash -i`) still shows a "sync" entry that should have been renamed as part of the sync→teleport migration. Additionally, there are no entries for plain `erk pr checkout` (local-first) or `erk pr teleport` (remote-first). The palette needs checkout and teleport entries to reflect the actual CLI command taxonomy.

## Changes

### File: `src/erk/tui/commands/registry.py`

**Remove:**
- `copy_pr_checkout` entry (lines 364-373) — the "sync" entry with `erk pr checkout --script --sync`

**Add display name generators:**

```python
def _display_copy_pr_checkout_script(ctx: CommandContext) -> str:
    if ctx.row.pr_number:
        return f'source "$(erk pr checkout {ctx.row.pr_number} --script)"'
    return "checkout"

def _display_copy_pr_checkout(ctx: CommandContext) -> str:
    if ctx.row.pr_number:
        return f"erk pr checkout {ctx.row.pr_number}"
    return "checkout"

def _display_copy_teleport(ctx: CommandContext) -> str:
    return f"erk pr teleport {ctx.row.pr_number}"

def _display_copy_teleport_new_slot(ctx: CommandContext) -> str:
    return f"erk pr teleport {ctx.row.pr_number} --new-slot"
```

**Add new COPY entries** (replacing the old sync entry in the same position):

| id | description | name | shortcut | command |
|----|-------------|------|----------|---------|
| `copy_pr_checkout_script` | `checkout (cd)` | `erk pr checkout --script` | `e` (reuse old sync shortcut) | `source "$(erk pr checkout {pr} --script)"` |
| `copy_pr_checkout_plain` | `checkout` | `erk pr checkout` | None | `erk pr checkout {pr}` |
| `copy_teleport` | `teleport` | `erk pr teleport` | None | `erk pr teleport {pr}` |
| `copy_teleport_new_slot` | `teleport (new slot)` | `erk pr teleport --new-slot` | None | `erk pr teleport {pr} --new-slot` |

All four entries: `is_available` requires `_is_plan_view(ctx) and ctx.row.pr_number is not None`.

**Also rename** the existing `_display_copy_pr_checkout` function to `_display_copy_pr_checkout_script` since we're splitting the concept. The existing `copy_checkout` entry (line 354-362, for `erk br co`) stays unchanged — it's the local-navigation-only entry.

## Verification

1. Run `erk dash -i`, select a PR row, open command palette
2. Confirm: no "sync" entry appears
3. Confirm: "checkout (cd)", "checkout", "teleport", "teleport (new slot)" entries appear in COPY section
4. Confirm: shortcut `e` triggers the checkout (cd) copy
5. Run tests: `pytest tests/tui/` for any command registry tests
