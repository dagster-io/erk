# Plan: Make next-steps `erk slot co` commands copy-pasteable

## Context

The `PrNextSteps` dataclass generates "new worktree" commands that aren't copy-pasteable. `erk slot co` runs in a subprocess, so its `chdir()` is invisible to the caller. The shell activation pattern (`source <(cmd --script)`) is required per `docs/learned/cli/shell-activation-pattern.md`.

## Changes

### 1. Update `PrNextSteps` properties

**File:** `packages/erk-shared/src/erk_shared/output/next_steps.py`

| Property | Current | New |
|---|---|---|
| `checkout_new_wt` (L27-28) | `erk slot co {branch}` | `source <(erk slot co {branch} --script)` |
| `implement_new_wt` (L43-44) | `erk slot co {branch} && erk implement` | `source <(erk slot co {branch} --script) && erk implement` |
| `implement_new_wt_dangerous` (L47-48) | `erk slot co {branch} && erk implement -d` | `source <(erk slot co {branch} --script) && erk implement -d` |

### 2. Update tests

**File:** `tests/unit/shared/test_next_steps.py`

- L35: `test_checkout_new_wt` — update expected string
- L50: `test_implement_new_wt` — update expected string
- L54: `test_implement_new_wt_dangerous` — update expected string
- L64: `test_contains_slot_co_command` — update `in` check

## Verification

- Run `pytest tests/unit/shared/test_next_steps.py`
