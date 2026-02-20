# Plan: Backend-Aware Command Palette in draft_pr Mode

## Context

The TUI command palette (Cmd+K) shows the same commands regardless of whether the plan backend is `"github"` or `"draft_pr"`. In draft_pr mode, the plan IS the draft PR — there is no backing issue. Issue-based commands like `prepare` and `implement` (which set up worktrees from issues) don't apply and shouldn't appear.

## Changes

### 1. Add `plan_backend` to `CommandContext`

**File:** `src/erk/tui/commands/types.py`

- Import `PlanBackendType` from `erk_shared.plan_store`
- Add `plan_backend: PlanBackendType` field to `CommandContext`

### 2. Add predicate and update 2 command availability checks

**File:** `src/erk/tui/commands/registry.py`

Add helper:

```python
def _is_github_backend(ctx: CommandContext) -> bool:
    return ctx.plan_backend == "github"
```

Update `is_available` for these 2 commands by adding `and _is_github_backend(ctx)`:

| Command ID              | Description                | Why hide                                                    |
| ----------------------- | -------------------------- | ----------------------------------------------------------- |
| `copy_prepare`          | Copy: `erk prepare <id>`   | Issue-based worktree setup; draft PRs already have branches |
| `copy_prepare_activate` | Copy: prepare && implement | Same — issue-based workflow                                 |

Commands that STAY available in both modes:

- `close_plan`, `submit_to_queue`, `fix_conflicts_remote`, `address_remote`, `land_pr`
- `open_issue` (plan_url = PR URL in draft_pr), `open_pr` (Graphite URL), `open_run`
- `copy_checkout`, `copy_pr_checkout`, `copy_submit`, `copy_replan`

### 3. Thread `plan_backend` through providers

**File:** `src/erk/tui/commands/provider.py`

**`MainListCommandProvider._get_context`:** Add `plan_backend=self._app._plan_backend` to `CommandContext(...)`.

**`PlanCommandProvider`:** Add `_app` property (same pattern as `MainListCommandProvider` already has) and add `plan_backend=self._app._plan_backend` to `CommandContext(...)`.

### 4. Update tests

**File:** `tests/tui/commands/test_registry.py`

- Add `plan_backend="github"` to all ~30 existing `CommandContext(...)` calls (required since frozen dataclass, no defaults)
- Rename `test_prepare_commands_always_available` to `test_prepare_commands_available_in_github_mode`
- Add `test_prepare_commands_hidden_in_draft_pr_mode` — verify 2 commands hidden
- Add `test_commands_available_in_draft_pr_mode` — verify kept commands still appear
- Extend `test_shortcuts_no_conflicts_within_view` to also check `plan_backend="draft_pr"`

## Verification

1. Run `pytest tests/tui/commands/test_registry.py` — all existing tests pass with `plan_backend="github"`
2. New draft_pr tests verify the 2 commands are hidden and remaining commands stay available
3. No shortcut collisions in draft_pr mode (hidden shortcuts: `"1"`, `"4"`)
