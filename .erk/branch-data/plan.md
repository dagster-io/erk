# Plan: Fix inaccuracies and complete howto/pr-checkout-sync.md

> **Replans:** #5984

## Context

The howto doc `docs/howto/pr-checkout-sync.md` was written during a remote implementation but contains several inaccurate flags, misleading command recommendations, and incomplete options tables. The doc references flags that don't exist (`--dry-run`, `--restack` on `erk pr co`) and omits important flags that do exist on all four commands.

## What Changed Since Original Plan

- The howto doc was written (144 lines) — the original plan's core goal is complete
- `--restack` flag was never implemented on `erk pr co`
- `--dry-run` flag was removed from `erk pr co`
- `erk pr sync` (no flags) is the proper git-only mode, not raw git commands
- Multiple new flags exist on commands that aren't documented

## Investigation Findings

### Corrections to Current Doc

1. **Line 25-26**: `erk pr co 123 --dry-run` — flag doesn't exist (not in `--help`)
2. **Line 39-40**: `--dry-run` and `--restack` flags listed — neither exists
3. **Lines 47-51**: Recommends `erk pr sync --dangerous` as primary, raw git as fallback — should recommend `erk pr sync` (no flags) for git-only, `--dangerous` for Graphite
4. **Line 101**: `gt submit --force --no-interactive` — should be `erk pr submit -f`
5. **Missing flags**: `--no-slot`, `-f/--force` on checkout; `--no-graphite`, `-f/--force` on submit; `--no-pull`, `--no-delete`, `--dry-run` on land

### Actual Command Flags (from --help)

| Command         | Flags                                                                |
| --------------- | -------------------------------------------------------------------- |
| `erk pr co`     | `--no-slot`, `-f/--force`                                            |
| `erk pr sync`   | `-d/--dangerous`                                                     |
| `erk pr submit` | `--no-graphite`, `-f/--force`, `--debug`, `--session-id`             |
| `erk land`      | `--up`, `-f/--force`, `--pull/--no-pull`, `--dry-run`, `--no-delete` |

## Implementation Steps

### 1. Fix `erk pr co` section (lines 14-41)

**File:** `docs/howto/pr-checkout-sync.md`

- Remove the `--dry-run` example (line 25-26)
- Replace flags table (lines 36-40) with actual flags: `--no-slot`, `-f/--force`
- Update command description to mention force-unassign behavior

### 2. Fix sync section (lines 42-65)

- Restructure to show `erk pr sync` (no flags) as the git-only mode
- Show `erk pr sync --dangerous` as the Graphite mode
- Add requirements note (must be on branch, PR must be open, no forks)

### 3. Fix submit section (lines 92-109)

- Replace `gt submit --force --no-interactive` with `erk pr submit -f`
- Add flags table: `--no-graphite`, `-f/--force`
- Keep `/local:quick-submit` reference

### 4. Expand land section (lines 111-128)

- Add flags table: `--up`, `-f/--force`, `--pull/--no-pull`, `--dry-run`, `--no-delete`
- Add target reference options (PR number, URL, branch name)

## Verification

- Run `make docs-build` to verify the doc builds correctly
- Visually confirm all flags match `--help` output for each command
