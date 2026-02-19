# Add `--no-interactive` to all `gt` subprocess calls

## Context

We're experiencing hangs in automation because several `gt` subprocess invocations are missing `--no-interactive`. Per AGENTS.md, `--interactive` is a **global option on ALL gt commands** (enabled by default), so every `gt` call must include `--no-interactive` to prevent prompting. Several calls already do this correctly (`gt submit`, `gt squash`), but others were missed.

## Inventory of all `gt` subprocess calls

| Command              | File                             | Has `--no-interactive`? |
| -------------------- | -------------------------------- | ----------------------- |
| `gt sync`            | `graphite/real.py:63`            | **NO**                  |
| `gt restack`         | `graphite/real.py:99`            | Conditional (param)     |
| `gt auth`            | `graphite/real.py:242`           | **NO**                  |
| `gt squash`          | `graphite/real.py:281`           | YES                     |
| `gt submit`          | `graphite/real.py:301`           | YES                     |
| `gt branch info`     | `graphite/real.py:342`           | **NO**                  |
| `gt continue`        | `graphite/real.py:352`           | **NO**                  |
| `gt track --branch`  | `branch_ops/real.py:37`          | **NO**                  |
| `gt delete -f`       | `branch_ops/real.py:45`          | **NO**                  |
| `gt submit --branch` | `branch_ops/real.py:66`          | YES                     |
| `gt track` (retrack) | `branch_ops/real.py:94`          | **NO**                  |
| `gt create`          | `wt/create_cmd.py:315`           | YES                     |
| `gt parent`          | `erk-dev codex_review:30`        | **NO**                  |
| `gt parent`          | `erk-dev branch_commit_count:15` | **NO**                  |

**9 of 14 calls are missing `--no-interactive`.**

## Changes

### 1. `packages/erk-shared/src/erk_shared/gateway/graphite/real.py`

- **`sync()` line 63**: `["gt", "sync"]` → `["gt", "sync", "--no-interactive"]`
- **`restack()` line 99**: Always include `--no-interactive` (remove conditional, see §6)
- **`check_auth_status()` line 242**: `["gt", "auth"]` → `["gt", "auth", "--no-interactive"]`
- **`is_branch_tracked()` line 342**: Add `"--no-interactive"` to command list
- **`continue_restack()` line 352**: `["gt", "continue"]` → `["gt", "continue", "--no-interactive"]`

### 2. `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/real.py`

- **`track_branch()` line 37**: Add `"--no-interactive"` to command list
- **`delete_branch()` line 45**: Add `"--no-interactive"` to command list
- **`retrack_branch()` line 94**: Add `"--no-interactive"` to command list

### 3. `packages/erk-dev/src/erk_dev/commands/codex_review/command.py` line 30

- `["gt", "parent"]` → `["gt", "parent", "--no-interactive"]`

### 4. `packages/erk-dev/src/erk_dev/commands/branch_commit_count/command.py` line 15

- `["gt", "parent"]` → `["gt", "parent", "--no-interactive"]`

### 5. Test assertions

Update tests that assert on exact command lists:

- `tests/real/test_real_graphite.py` — `gt sync` and `gt branch info` assertions
- `tests/integration/test_real_graphite_branch_ops.py` — `gt track` and `gt delete` assertions

### 6. Remove `no_interactive` parameter from `restack()` (always-on)

Every caller already passes `no_interactive=True`. Remove the parameter and hardcode `--no-interactive`:

**Files to update:**

- `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py` — Remove `no_interactive` from `restack()` and `restack_idempotent()` signatures
- `packages/erk-shared/src/erk_shared/gateway/graphite/real.py` — Hardcode `--no-interactive` in `restack()`
- `packages/erk-shared/src/erk_shared/gateway/graphite/fake.py` — Remove param from `restack()`, update `_restack_calls` type
- `packages/erk-shared/src/erk_shared/gateway/graphite/dry_run.py` — Remove param from `restack()`
- `packages/erk-shared/src/erk_shared/gateway/graphite/printing.py` — Remove param from `restack()` wrapper
- `src/erk/cli/commands/pr/sync_cmd.py` — Remove `no_interactive=True` from callers (lines 236, 304)
- `tests/real/test_real_graphite.py` — Update restack test
- `tests/unit/gateways/graphite/test_graphite_disabled.py` — Update restack call

## Verification

1. `rg '"gt"' --type py | grep -v no-interactive | grep -v test` — confirm all production gt calls have it
2. `make fast-ci` — run tests to catch regressions
