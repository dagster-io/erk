# Plan: Split Ensure into Ensure + EnsureIdeal

## Goal

Split `Ensure` into two classes to clarify semantics:
- **`Ensure`** — invariant/precondition checks (12 methods, stays in `ensure.py`)
- **`EnsureIdeal`** — non-ideal-state type narrowing (7 methods, new file `ensure_ideal.py`)

## Methods Moving to EnsureIdeal

| Method | Call sites |
|--------|-----------|
| `ideal_state` | 0 |
| `branch` | 0 |
| `pr` | 0 |
| `unwrap_pr` | 4 (all in `land_cmd.py`) |
| `comments` | 0 |
| `void_op` | 0 |
| `session` | 1 (`show_cmd.py`) |

## Files to Modify

1. **`src/erk/cli/ensure_ideal.py`** (NEW) — Create `EnsureIdeal` class with the 7 methods, plus needed imports from `erk_shared`
2. **`src/erk/cli/ensure.py`** — Remove the 7 methods and their specific imports (`NonIdealState`, `BranchDetectionFailed`, `GitHubAPIFailed`, `NoPRForBranch`, `PRNotFoundError`, `SessionNotFound`, `PRDetails`, `PRNotFound`)
3. **`src/erk/cli/commands/land_cmd.py`** — Update 4 `Ensure.unwrap_pr(` → `EnsureIdeal.unwrap_pr(`, add import
4. **`src/erk/cli/commands/cc/session/show_cmd.py`** — Update 1 `Ensure.session(` → `EnsureIdeal.session(`, add import
5. **`tests/unit/cli/test_ensure.py`** — Move `TestEnsureUnwrapPr` tests to new `tests/unit/cli/test_ensure_ideal.py`, update imports

## Steps

1. Create `src/erk/cli/ensure_ideal.py` with `EnsureIdeal` class containing the 7 methods
2. Remove those 7 methods from `src/erk/cli/ensure.py` and clean up unused imports
3. Update `land_cmd.py` imports and 4 call sites
4. Update `show_cmd.py` import and 1 call site
5. Create `tests/unit/cli/test_ensure_ideal.py` with moved tests
6. Remove moved tests from `tests/unit/cli/test_ensure.py`
7. Run CI: `make fast-ci` to verify

## Verification

- `make fast-ci` passes (lint, format, type check, unit tests)