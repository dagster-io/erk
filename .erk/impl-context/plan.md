# Add "implement locally" copyable command to TUI command palette

## Context

The `erk dash` TUI command palette has a `copy_prepare_activate` command that copies `source "$(erk br co --for-plan {id} --script)" && erk implement --dangerous` to clipboard, but it's only available for github-backend plans (`_is_github_backend` predicate). For draft_pr-backend plans (remote plans with PRs), there's no way to copy a local implement command. The user wants a copyable command to implement these remote plans locally.

## Plan

Add a `copy_implement_local` COPY command that checks out the PR and runs implement. Available when the plan has a PR and uses the draft_pr backend.

**Command string**: `source "$(erk pr checkout {pr_number} --script)" && erk implement --dangerous`

### Files to modify

#### 1. `src/erk/tui/commands/registry.py`
- Add display name generator `_display_copy_implement_local` (after `_display_copy_prepare_activate`, ~line 112):
  ```python
  def _display_copy_implement_local(ctx: CommandContext) -> str:
      return (
          f'source "$(erk pr checkout {ctx.row.pr_number} --script)"'
          " && erk implement --dangerous"
      )
  ```
- Add `CommandDefinition` in the PLAN COPIES section, right after `copy_prepare_activate` (~line 349):
  ```python
  CommandDefinition(
      id="copy_implement_local",
      name="checkout && implement",
      description="implement",
      category=CommandCategory.COPY,
      shortcut="2",
      is_available=lambda ctx: (
          _is_plan_view(ctx)
          and not _is_github_backend(ctx)
          and ctx.row.pr_number is not None
      ),
      get_display_name=_display_copy_implement_local,
  ),
  ```

#### 2. `src/erk/tui/app.py`
- Add handler in `execute_palette_command`, after the `copy_prepare_activate` block (~line 841):
  ```python
  elif command_id == "copy_implement_local":
      if row.pr_number is not None:
          cmd = (
              f'source "$(erk pr checkout {row.pr_number} --script)"'
              " && erk implement --dangerous"
          )
          self._provider.clipboard.copy(cmd)
          self.notify(f"Copied: {cmd}")
  ```

#### 3. `src/erk/tui/screens/plan_detail_screen.py`
- Add binding (~line 50, after `copy_prepare_activate`):
  ```python
  Binding("2", "copy_implement_local", "Implement Local"),
  ```
- Add `action_copy_implement_local` method (after `action_copy_prepare_activate`, ~line 350):
  ```python
  def action_copy_implement_local(self) -> None:
      """Copy one-liner to checkout PR and start local implementation."""
      if self._row.pr_number is not None:
          cmd = (
              f'source "$(erk pr checkout {self._row.pr_number} --script)"'
              " && erk implement --dangerous"
          )
          self._copy_and_notify(cmd)
  ```
- Add handler in `execute_command`, after `copy_prepare_activate` block (~line 645):
  ```python
  elif command_id == "copy_implement_local":
      if row.pr_number is not None:
          cmd = (
              f'source "$(erk pr checkout {row.pr_number} --script)"'
              " && erk implement --dangerous"
          )
          executor.copy_to_clipboard(cmd)
          executor.notify(f"Copied: {cmd}", severity=None)
  ```

## Verification

1. Run `erk dash -i` and select a draft_pr-backed plan with a PR
2. Open command palette — verify "implement" appears with the clipboard icon
3. Select it — verify the correct command is copied to clipboard
4. Press `2` shortcut in plan detail screen — verify same behavior
5. Select a github-backed plan — verify the new command does NOT appear (existing `copy_prepare_activate` appears instead)
