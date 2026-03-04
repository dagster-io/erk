# Plan: Skip `source activate.sh` When Already in Target Worktree

## Context

When running commands like `erk down -f -d`, `erk wt co`, or `erk br co` and the target worktree is the **same physical directory** the user is already in (e.g., same slot, different branch), the output unnecessarily shows:

```
source /path/to/activate.sh && erk br delete plnd/old-branch -f
```

Since the user is already in that directory with their venv activated, they just need `erk br delete plnd/old-branch -f`. The `source` prefix is noise.

This affects **all 5 interactive-mode call sites** that print activation instructions, not just navigation.

## Approach

Add a `same_worktree: bool` parameter to `print_activation_instructions()` and `build_activation_command()`. Each caller computes it by comparing `target_path.resolve()` to `ctx.cwd.resolve()`. When same-worktree, skip the `source activate.sh &&` prefix.

## Implementation

### File: `src/erk/cli/activation.py`

**1. `print_activation_instructions()` (line 312)** — Add `same_worktree: bool = False` parameter:

```python
def print_activation_instructions(
    script_path: Path,
    *,
    source_branch: str | None,
    force: bool,
    config: ActivationConfig,
    copy: bool,
    same_worktree: bool = False,
) -> None:
```

In the body, when `same_worktree=True`:
- Delete branch case: use `erk br delete {source_branch} -f` (no source prefix), instruction `"To delete branch {source_branch}:"`
- Activate-only case: use `build_activation_command(config, script_path, same_worktree=same_worktree)` which returns just `erk implement ...` or skips entirely

**2. `build_activation_command()` (line 57)** — Add `same_worktree: bool = False` parameter:

When `same_worktree=True`:
- If not implement mode: return empty string (nothing to run — already activated)
- If implement mode: return just `erk implement [flags]` (no `source` prefix)

When `same_worktree=True` and not implement mode and no source_branch, the whole instruction block can be suppressed. Add early return in `print_activation_instructions()`.

### File: `src/erk/cli/commands/navigation_helpers.py`

**3. `activate_target()` (line 332)** — Compute same-worktree and pass it:

```python
# After line 355 (Ensure.path_exists)
same_worktree = target_path.resolve() == ctx.cwd.resolve()
```

Pass `same_worktree=same_worktree` to `print_activation_instructions()` on line 399.

**4. `_activate_with_deferred_deletion()` (line 853)** — Same pattern:

```python
same_worktree = target_path.resolve() == ctx.cwd.resolve()
```

Pass to `print_activation_instructions()` on line 917.

### File: `src/erk/cli/commands/wt/checkout_cmd.py`

**5. `wt_checkout()` (line 117)** — Compute and pass:

```python
same_worktree = worktree_path.resolve() == ctx.cwd.resolve()
```

Pass to `print_activation_instructions()` on line 123. When same-worktree with no source_branch and activate-only config, suppress the entire activation block (nothing to do).

### File: `src/erk/cli/commands/branch/checkout_cmd.py`

**6. `_perform_checkout()` (line 247)** — Compute and pass:

```python
same_worktree = target_path.resolve() == ctx.cwd.resolve()
```

Pass to `print_activation_instructions()` on line 256.

### File: `src/erk/cli/commands/wt/create_from_cmd.py`

**7. `create_from_wt()` (line 92)** — Compute and pass:

```python
same_worktree = result.worktree_path.resolve() == ctx.cwd.resolve()
```

Pass to `print_activation_instructions()` on line 109.

## Critical Files

- `src/erk/cli/activation.py` — `print_activation_instructions()`, `build_activation_command()`
- `src/erk/cli/commands/navigation_helpers.py` — `activate_target()`, `_activate_with_deferred_deletion()`
- `src/erk/cli/commands/wt/checkout_cmd.py` — `wt_checkout()`
- `src/erk/cli/commands/branch/checkout_cmd.py` — `_perform_checkout()`
- `src/erk/cli/commands/wt/create_from_cmd.py` — `create_from_wt()`

## Behavior Summary

| Scenario | Same worktree? | Current output | New output |
|---|---|---|---|
| `erk down -f -d` to same slot | Yes | `source activate.sh && erk br delete branch -f` | `erk br delete branch -f` |
| `erk down` to different slot | No | `source activate.sh` | `source activate.sh` (unchanged) |
| `erk wt co` to same worktree | Yes | `source activate.sh` | Nothing (already there) |
| `erk br co` to same worktree | Yes | `source activate.sh` | Nothing (already there) |

## Verification

1. From a slot worktree, run `erk down -f -d` where target is same slot — confirm no `source` prefix
2. From a slot worktree, run `erk down` where target is a different slot — confirm `source` prefix still shown
3. Run `erk wt co <current-worktree>` — confirm no activation instructions shown
4. Run `erk br co <branch-in-different-worktree>` — confirm `source` prefix still shown
5. Run existing tests: `pytest tests/ -k "navigation or activation or checkout"`
