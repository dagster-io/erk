# Consolidate checkout/implementation-setup flow + fix Graphite divergence

## Context

`erk pr checkout` causes Graphite divergence for stacked PRs (retracks before rebase). Meanwhile, the checkout/implementation-setup flow is fragmented across 6+ entry points with overlapping responsibilities. The user wants to:

1. Fix the Graphite divergence bug
2. Add `erk pr prepare` as the clean way to set up impl-context for a checked-out PR
3. Rationalize the relationship between the overlapping commands

## Current Landscape

| Command | Checkout? | Worktree? | Rebase stacked? | Graphite? | Impl-context? |
|---|---|---|---|---|---|
| `erk pr checkout <N>` | Yes | Yes | Yes (buggy) | Yes (buggy) | No |
| `erk pr checkout P<N>` | Yes | Yes | No | No | No |
| `erk br co --for-plan <N>` | Yes | Yes | Yes (correct) | Yes (correct) | Yes |
| `erk exec setup-impl` | Yes | No | No | No | Yes |
| `erk exec setup-impl-from-pr` | Yes | No | No | No | Yes |

The intended clean flow after this change:
```
erk pr checkout <N>     →  get code into a worktree (fix Graphite bug here)
erk pr prepare [<N>]    →  set up impl-context for current worktree's PR
```

## Changes

### Step 1: Fix Graphite divergence in `erk pr checkout`

**File:** `src/erk/cli/commands/pr/checkout_cmd.py`

**Bug:** Lines 256-262 retrack with Graphite before the stacked-PR rebase at line 283. Graphite's cached SHA becomes stale after rebase.

**Fix:** Remove the early retrack block (lines 256-262). Move all Graphite tracking to after the rebase block (after line 290), consolidating the "already tracked" and "untracked" cases into one block. The flow becomes:

```
fetch + force-update → create worktree → rebase (if stacked) → retrack/track
```

For stacked PRs where the parent branch exists locally but is stale, also add `update_local_ref` logic matching `_rebase_and_track_for_plan()` (branch/checkout_cmd.py:381-388).

**Test update:** `tests/commands/pr/test_checkout_graphite_linking.py`
- Update `test_pr_checkout_retracks_diverged_graphite_branch` (line 232) — its docstring explicitly says retrack happens "before worktree creation or rebase", which is the buggy behavior. Update to verify retrack happens after rebase.
- Add a new test for stacked PR checkout that verifies rebase-then-track ordering.

### Step 2: Extract shared impl-context creation logic

**File:** `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py`

Extract the "read plan content and create impl folder" portion of `_setup_planned_pr_plan()` into a standalone function:

```python
def create_impl_context_from_pr(
    ctx: click.Context,
    *,
    plan_number: int,
    cwd: Path,
    branch_name: str,
) -> dict[str, str | int | bool | None]:
```

This function:
- Fetches PR metadata, reads plan content (from committed `.erk/impl-context/` files or PR body fallback)
- Creates `.erk/impl-context/<branch>/` with plan.md and ref.json
- Does NOT checkout branches or create worktrees

Have `_setup_planned_pr_plan()` call this after its branch checkout logic.

### Step 3: Create `erk pr prepare` command

**New file:** `src/erk/cli/commands/pr/prepare_cmd.py`

```
erk pr prepare [PLAN_NUMBER]
```

Behavior:
- Must be run from inside a worktree
- If `PLAN_NUMBER` omitted: detect from current branch's PR (via `ctx.github.get_pr_for_branch()`)
- Calls `create_impl_context_from_pr()` from Step 2
- Idempotent: if impl-context already exists for this plan, reports success without recreating

**Register in:** `src/erk/cli/commands/pr/__init__.py` — add import and `pr_group.add_command(pr_prepare, name="prepare")`

**New test file:** `tests/commands/pr/test_prepare.py`
- Test auto-detection from current branch
- Test explicit plan number
- Test error when not on a plan branch and no number provided
- Test idempotent behavior (impl-context already exists)

### Step 4: Update references

- `src/erk/cli/commands/pr/checkout_cmd.py` line 371: The `_checkout_plan` error message says `erk br co --for-plan {plan_number}` — add `erk pr prepare` as alternative
- Do NOT deprecate `erk br co --for-plan` yet (it has extensive TUI references). That's a follow-up.

## Files Modified

- `src/erk/cli/commands/pr/checkout_cmd.py` — fix Graphite ordering, update help text
- `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py` — extract shared function
- `src/erk/cli/commands/pr/prepare_cmd.py` — **new** command
- `src/erk/cli/commands/pr/__init__.py` — register new command
- `tests/commands/pr/test_checkout_graphite_linking.py` — update/add tests
- `tests/commands/pr/test_prepare.py` — **new** test file

## Files NOT Modified

- `erk exec setup-impl` / `erk exec setup-impl-from-pr` — must remain as-is for CI and skill compatibility
- `erk br co --for-plan` — deprecation is a follow-up
- `erk implement` — orthogonal command
- `.github/workflows/plan-implement.yml` — uses exec commands, unaffected

## Verification

1. Run Graphite linking tests: `pytest tests/commands/pr/test_checkout_graphite_linking.py`
2. Run prepare tests: `pytest tests/commands/pr/test_prepare.py`
3. Run all PR checkout tests: `pytest tests/commands/pr/ -k checkout`
4. Manual: `erk pr checkout <stacked-pr>` then `gt ls` — no divergence warning
5. Manual: `erk pr checkout <N>` then `erk pr prepare` — creates impl-context
