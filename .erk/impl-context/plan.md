# Rename submit to dispatch in gateway ABCs and TUI callers

Part of Objective #8241 (Migrate Remote Execution Terminology from Submit to Dispatch), Nodes 2.1–2.5.

## Context

Phase 1 (nodes 1.1–1.3, PR #8248) already updated the external-facing commands (`erk pr dispatch` CLI). Phase 2 renames the internal Python identifiers — ABC methods, implementation classes, properties, constants, and their callers — to match the new "dispatch" terminology. Phase 3 (separate PR) will handle command IDs, display functions, toast messages, and key mappings.

## Scope Boundary

- **In scope:** Python method/variable/property/constant renames, updating all callers, and updating tests that reference renamed symbols.
- **Out of scope:** Command ID strings (`"submit_to_queue"`), user-facing toast messages, display function names in registry, launch_screen key mappings, markdown headings — all Phase 3.

## Changes

### 1. CommandExecutor ABC + Real + Fake (Node 2.1)

**`packages/erk-shared/src/erk_shared/gateway/command_executor/abc.py`**
- Rename method `submit_to_queue` → `dispatch_to_queue`
- Update docstring: "Submit plan" → "Dispatch plan"

**`packages/erk-shared/src/erk_shared/gateway/command_executor/real.py`**
- Rename constructor param `submit_to_queue_fn` → `dispatch_to_queue_fn`
- Rename instance var `_submit_to_queue_fn` → `_dispatch_to_queue_fn`
- Rename method `submit_to_queue` → `dispatch_to_queue`
- Update docstrings

**`packages/erk-shared/src/erk_shared/gateway/command_executor/fake.py`**
- Rename instance var `_submitted_to_queue` → `_dispatched_to_queue`
- Rename property `submitted_to_queue` → `dispatched_to_queue`
- Rename method `submit_to_queue` → `dispatch_to_queue`
- Update docstrings

### 2. PlanDataProvider ABC + Real + Fake (Node 2.2)

**`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py`**
- Rename method `submit_to_queue` → `dispatch_to_queue`

**`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`**
- Rename method `submit_to_queue` → `dispatch_to_queue`

**`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`**
- Rename method `submit_to_queue` → `dispatch_to_queue`
- Update comment: "submit" → "dispatch"

### 3. NextSteps Properties (Node 2.3)

**`packages/erk-shared/src/erk_shared/output/next_steps.py`**
- Rename `IssueNextSteps.submit` property → `dispatch`
- Rename `PlannedPRNextSteps.submit` property → `dispatch`
- Update `s.submit` → `s.dispatch` in `format_next_steps_plain`, `format_planned_pr_next_steps_plain`, `format_next_steps_markdown`

### 4. SUBMIT_SLASH_COMMAND Constant (Node 2.4)

**`packages/erk-shared/src/erk_shared/output/next_steps.py`**
- Rename `SUBMIT_SLASH_COMMAND` → `DISPATCH_SLASH_COMMAND`
- Update references in format functions

### 5. TUI Callers (Node 2.5)

**`src/erk/tui/app.py`**
- Rename method `_submit_to_queue_async` → `_dispatch_to_queue_async`
- Update 2 `RealCommandExecutor(...)` calls: `submit_to_queue_fn=self._provider.submit_to_queue` → `dispatch_to_queue_fn=self._provider.dispatch_to_queue` (lines ~786, ~1095)
- Update caller `self._submit_to_queue_async(row.plan_id)` → `self._dispatch_to_queue_async(row.plan_id)` (line ~1133)
- Keep command_id comparison string `"submit_to_queue"` unchanged (Phase 3)
- Keep toast message "Submitting plan" unchanged (Phase 3)

**`src/erk/tui/screens/plan_detail_screen.py`**
- Update `self.app._submit_to_queue_async(row.plan_id)` → `self.app._dispatch_to_queue_async(row.plan_id)` (line ~730)

### 6. Tests for Renamed Symbols

**`tests/tui/test_app.py`**
- Rename test class/methods referencing `_submit_to_queue_async` → `_dispatch_to_queue_async` (lines ~2512–2600)

**`tests/unit/shared/test_next_steps.py`**
- Update `steps.submit` → `steps.dispatch` (line ~61)

**Tests NOT modified (Phase 3):**
- `tests/tui/commands/test_registry.py` — command ID strings
- `tests/tui/commands/test_execute_command.py` — command ID strings
- `tests/tui/screens/test_launch_screen.py` — command ID strings

## File Summary (12 files)

| # | File | Change Type |
|---|------|-------------|
| 1 | `packages/erk-shared/src/erk_shared/gateway/command_executor/abc.py` | Method rename |
| 2 | `packages/erk-shared/src/erk_shared/gateway/command_executor/real.py` | Method + param + var rename |
| 3 | `packages/erk-shared/src/erk_shared/gateway/command_executor/fake.py` | Method + var + property rename |
| 4 | `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py` | Method rename |
| 5 | `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` | Method rename |
| 6 | `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` | Method rename |
| 7 | `packages/erk-shared/src/erk_shared/output/next_steps.py` | Property + constant rename |
| 8 | `src/erk/tui/app.py` | Method rename + caller updates |
| 9 | `src/erk/tui/screens/plan_detail_screen.py` | Caller update |
| 10 | `tests/tui/test_app.py` | Test updates |
| 11 | `tests/unit/shared/test_next_steps.py` | Test updates |

## Verification

1. Run `make fast-ci` (unit tests + type checking + linting)
2. Specifically verify: `pytest tests/tui/test_app.py tests/unit/shared/test_next_steps.py -v`
3. Run `ty` type checker to confirm no broken references
