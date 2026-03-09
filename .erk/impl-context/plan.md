# Plan: Add progress output to `erk land` validation and execution

## Context

`erk land` (both single-branch and `--stack`) silently runs multiple validation steps before any mutations. Users see no feedback about what checks are passing, making the command feel opaque — especially in `--dry-run` mode where the whole point is to preview what would happen. Adding step-by-step progress output builds trust by teaching users what the command validates.

## Approach

Add `user_output()` calls with dim-styled status messages at each validation and execution step, matching the existing pattern from `submit_pipeline.py` (e.g., `click.style("   Resolving branch and plan context...", dim=True)`).

### Output style

Use the established erk pattern:
- **Dim text** for in-progress step announcements: `click.style("  Checking ...", dim=True)`
- **Green checkmark** for completed actions: `click.style("✓", fg="green") + " ..."`
- **Indentation**: 2-space indent for validation steps to visually group them under the command

### Files to modify

#### 1. `src/erk/cli/commands/land_stack.py` — Stack land

**In `_prepare_stack_land()` (lines 154-220)** — add progress output after each validation:

| After line | Message |
|---|---|
| 162 | `"  Working tree is clean"` (green check) |
| 168 | `"  Graphite stack management confirmed"` (green check) |
| 177 | `"  Current branch: {current_branch}"` (green check) |
| 194 | `"  Stack has {len(stack)-1} branch(es) to land"` (green check) |

**In `_validate_stack_entries()` (lines 223-287)** — add per-entry progress:

| Location | Message |
|---|---|
| Before the loop (after line 232) | `"  Validating stack entries..."` (dim) |
| After line 240 (PR found) | `"    PR #{pr_details.number} [{branch}]: found"` (dim) |
| After line 248 (state=OPEN) | (fold into above) |
| After line 256 (base matches) | (fold into above) |
| After successful entry append (line 278) | `"  ✓ PR #{pr_details.number} [{branch}]: open, base correct, clean"` (green check) |

**In execution loop (lines 87-151)** — add progress for currently silent steps:

| Location | Message |
|---|---|
| Before rebase (line 89) | `"  Rebasing {entry.branch} onto {trunk_branch}..."` (dim) |
| After successful rebase+push (end of `_rebase_entry_onto_trunk`) | `"  ✓ Rebased {branch} onto {trunk_branch}"` (green check) |
| Before reparent (line 100) | `"  Reparenting {len(child_branches)} child branch(es)..."` (dim) |
| After successful reparent (end of `_reparent_children_for_stack`) | `"  ✓ Reparented children to {trunk_branch}"` (green check) |

**In `_cleanup_stack_after_success()` (lines 539-576)** — add progress:

| Location | Message |
|---|---|
| Before cleanup loop | `"  Cleaning up {len(plan.entries)} branch(es)..."` (dim) |

#### 2. `src/erk/cli/commands/land_pipeline.py` — Single-branch land

**In validation pipeline steps** — add progress output in each step function:

| Step function | Message |
|---|---|
| `resolve_target()` end (before return) | `"  ✓ Target: PR #{pr_details.number} [{branch}]"` |
| `validate_pr()` after state check (line 312) | `"  ✓ PR #{state.pr_number} is open"` |
| `validate_pr()` after base check (line 324) | `"  ✓ PR base targets trunk"` |
| `resolve_plan_id()` end | `"  ✓ Plan context resolved"` or `"  No linked plan"` (dim) |
| `resolve_objective()` end | `"  ✓ Linked to objective #{n}"` or omit if None |

**In execution pipeline steps** — add progress for `merge_pr()`:

| Location | Message |
|---|---|
| Before merge (line 404, existing) | Already has `"Merging PR #..."` — keep as-is |

### What NOT to change

- The `_display_stack_summary()` output stays as-is (it's the final summary before action)
- Error messages via `Ensure.invariant()` stay as-is
- The `[DRY RUN] No changes made` banner stays as-is
- Confirmation prompts stay as-is

## Example output (stack dry-run)

```
  ✓ Working tree is clean
  ✓ Graphite stack management confirmed
  ✓ Current branch: plnd/unify-launch-remotegithub-03-08-1420
  ✓ Stack has 2 branch(es) to land
  Validating stack entries...
  ✓ PR #9019 [plnd/O8832-launch-no-repo-remot-03-08-1454]: open, base correct, clean
  ✓ PR #9021 [plnd/unify-launch-remotegithub-03-08-1420]: open, base correct, clean

Landing 2 PR(s) bottom-up:

  1. PR #9019 [plnd/O8832-launch-no-repo-remot-03-08-1454]
  2. PR #9021 [plnd/unify-launch-remotegithub-03-08-1420]

Local cleanup: enabled after full success

[DRY RUN] No changes made
```

## Example output (stack execution)

```
  ✓ Working tree is clean
  ✓ Graphite stack management confirmed
  ✓ Current branch: plnd/unify-launch-remotegithub-03-08-1420
  ✓ Stack has 2 branch(es) to land
  Validating stack entries...
  ✓ PR #9019 [plnd/O8832-launch-no-repo-remot-03-08-1454]: open, base correct, clean
  ✓ PR #9021 [plnd/unify-launch-remotegithub-03-08-1420]: open, base correct, clean

Landing 2 PR(s) bottom-up:

  1. PR #9019 [plnd/O8832-launch-no-repo-remot-03-08-1454]
  2. PR #9021 [plnd/unify-launch-remotegithub-03-08-1420]

Local cleanup: enabled after full success

✓ Merged PR #9019 [plnd/O8832-launch-no-repo-remot-03-08-1454] (1/2)
  Rebasing plnd/unify-launch-remotegithub-03-08-1420 onto master...
  ✓ Rebased onto master
✓ Merged PR #9021 [plnd/unify-launch-remotegithub-03-08-1420] (2/2)
  Cleaning up 2 branch(es)...

✓ Stack landed: 2 PR(s) merged successfully
```

## Verification

1. Run `erk land --dry-run --stack` and verify all validation steps print with checkmarks
2. Run `erk land --dry-run` (single-branch) and verify validation steps print
3. Run the existing land tests to ensure no regressions
4. Visually verify output is readable and not too noisy
