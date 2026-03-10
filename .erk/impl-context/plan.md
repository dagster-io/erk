# Plan: Add Cancel and Retry Commands for Workflow Runs

## Context

The TUI runs tab (view 4) currently has no command palette — it's explicitly disabled because the palette system only works with `PlanRowData`. Users viewing workflow runs have no way to cancel in-progress runs or retry failed ones without leaving the TUI. Adding these as CLI commands (`erk workflow run cancel`, `erk workflow run retry`) and wiring them into the runs tab command palette completes the runs tab as an interactive surface.

## Step 1: Gateway Layer (4-file pattern)

Add two new abstract methods to `LocalGitHub`:

**`packages/erk-shared/src/erk_shared/gateway/github/abc.py`**
- `cancel_workflow_run(self, repo_root: Path, run_id: str) -> None`
- `rerun_workflow_run(self, repo_root: Path, run_id: str, *, failed_only: bool) -> None`

**`packages/erk-shared/src/erk_shared/gateway/github/real.py`**
- Cancel: `gh api --method POST repos/{owner}/{repo}/actions/runs/{run_id}/cancel`
- Rerun: `gh api --method POST repos/{owner}/{repo}/actions/runs/{run_id}/rerun` (or `/rerun-failed-jobs` when `failed_only=True`)
- Use `execute_gh_command_with_retry` pattern (matching `list_workflow_runs` at line 602)

**`packages/erk-shared/src/erk_shared/gateway/github/dry_run.py`**
- Both are mutations — implement as `pass` (no-op)

**`tests/fakes/gateway/github.py`**
- Add `_cancelled_run_ids: list[str]` and `_rerun_run_ids: list[tuple[str, bool]]` mutation tracking
- Expose via read-only properties for test assertions

## Step 2: CLI Commands

Commands live under `erk workflow run` (existing group at `src/erk/cli/commands/run/`).

**`src/erk/cli/commands/run/cancel_cmd.py`** (new)
- Click command: `erk workflow run cancel <RUN_ID>`
- Access gateway via `ErkContext`, call `ctx.github.cancel_workflow_run()`
- Print confirmation message on success

**`src/erk/cli/commands/run/retry_cmd.py`** (new)
- Click command: `erk workflow run retry <RUN_ID> [--failed]`
- `--failed` flag reruns only failed jobs
- Access gateway via `ErkContext`, call `ctx.github.rerun_workflow_run()`
- Print confirmation message on success

**`src/erk/cli/commands/run/__init__.py`**
- Register both new commands via `run_group.add_command()`

## Step 3: TUI Command Palette for Runs Tab

### 3a. New RunCommandContext type

**`src/erk/tui/commands/types.py`**
- Add `RunCommandContext` dataclass (frozen) with `row: RunRowData` and `view_mode: ViewMode`
- Keep existing `CommandContext` unchanged (no union type pollution)

### 3b. Run command definitions

**`src/erk/tui/commands/registry.py`**
- Add `get_all_run_commands() -> list[CommandDefinition]` returning run-specific commands
- Add `get_available_run_commands(ctx: RunCommandContext) -> list[CommandDefinition]`
- Reuse `CommandDefinition` type (the `is_available` callable works with any context at runtime)

Run commands to add:

| ID | Category | Description | Availability |
|---|---|---|---|
| `cancel_run` | ACTION | cancel | status in ("queued", "in_progress") |
| `retry_run` | ACTION | retry | completed + conclusion in ("failure", "cancelled") |
| `retry_failed_run` | ACTION | retry failed | same as retry_run |
| `open_run_url` | OPEN | run | run_url is not None |
| `open_run_pr` | OPEN | pr | pr_url is not None |
| `copy_cancel_cmd` | COPY | cancel | status in ("queued", "in_progress") |
| `copy_retry_cmd` | COPY | retry | completed + conclusion in ("failure", "cancelled") |

Display names: `erk workflow run cancel {run_id}`, `erk workflow run retry {run_id}`, `erk workflow run retry {run_id} --failed`

### 3c. Provider changes

**`src/erk/tui/commands/provider.py`**
- Modify `MainListCommandProvider._get_context()` return type to `CommandContext | RunCommandContext | None`
- When `ViewMode.RUNS`: build `RunCommandContext` from `_get_selected_run_row()` instead of returning None
- In `discover()` and `search()`: dispatch to `get_available_run_commands()` when context is `RunCommandContext`

### 3d. Palette execution

**`src/erk/tui/actions/palette.py`**
- Add run command handling block at top of `execute_palette_command()`:
  - If command_id starts with a run-specific prefix, get `RunRowData` via `_get_selected_run_row()`
  - `cancel_run` → `_start_operation()` + `_cancel_run_async()`
  - `retry_run` → `_start_operation()` + `_retry_run_async(op_id, run_id, failed_only=False)`
  - `retry_failed_run` → `_start_operation()` + `_retry_run_async(op_id, run_id, failed_only=True)`
  - `open_run_url` → `self._service.browser.launch(run_row.run_url)`
  - `open_run_pr` → `self._service.browser.launch(run_row.pr_url)`
  - Copy commands → `self._service.clipboard.copy(text)`

### 3e. Background workers

**`src/erk/tui/operations/workers.py`**
- Add `_cancel_run_async(self, op_id, run_id)` — `@work(thread=True)`, calls CLI via subprocess (`["erk", "workflow", "run", "cancel", run_id]`), follows `_close_plan_async` error boundary pattern (try/except with toast)
- Add `_retry_run_async(self, op_id, run_id, *, failed_only)` — same pattern with `["erk", "workflow", "run", "retry", run_id]` (+ `"--failed"` flag)
- Both refresh data on success via `self.call_from_thread(self.action_refresh)`

## Step 4: Tests

- Gateway fake: verify mutation tracking for cancel/rerun
- CLI commands: test with FakeLocalGitHub
- TUI command availability predicates: verify cancel only for queued/in_progress, retry only for completed+failure/cancelled
- TUI palette integration: pilot test that command palette shows run commands on Runs tab

## Verification

1. `erk workflow run cancel <id>` and `erk workflow run retry <id>` work from CLI
2. `erk dash -i` → switch to Runs tab (key 4) → Ctrl+P opens palette with run-specific commands
3. Cancel shows only for in-progress/queued runs; retry shows only for failed/cancelled runs
4. Run `make fast-ci` to verify all tests pass

## Critical Files

- `packages/erk-shared/src/erk_shared/gateway/github/abc.py`
- `packages/erk-shared/src/erk_shared/gateway/github/real.py`
- `packages/erk-shared/src/erk_shared/gateway/github/dry_run.py`
- `tests/fakes/gateway/github.py`
- `src/erk/cli/commands/run/__init__.py`
- `src/erk/cli/commands/run/cancel_cmd.py` (new)
- `src/erk/cli/commands/run/retry_cmd.py` (new)
- `src/erk/tui/commands/types.py`
- `src/erk/tui/commands/registry.py`
- `src/erk/tui/commands/provider.py`
- `src/erk/tui/actions/palette.py`
- `src/erk/tui/operations/workers.py`
