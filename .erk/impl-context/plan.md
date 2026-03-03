# Plan: Auto-execute activation scripts in interactive mode

## Context

Currently, many commands print activation instructions requiring manual copy-paste:
```
To activate the worktree environment:
  source /path/to/.erk/bin/activate.sh  (copied to clipboard)
```

While the command is copied to clipboard via OSC 52, the next step is to automatically execute the activation script in interactive mode rather than requiring manual intervention.

### User's Request
Audit the codebase for all instances where this pattern occurs and create a unified solution to eliminate unnecessary manual "source" steps.

## Root Cause Analysis

The codebase has a **dual-mode architecture**:
- **Script mode (`--script` flag)**: Generates script and outputs path for shell integration
- **Interactive mode (default)**: Prints activation instructions with clipboard copy

In interactive mode, the activation script is already copied to clipboard, but users still need to manually paste and run it. The next logical step is to auto-execute.

## Instances Found

| Location | Command | Current Behavior |
|----------|---------|------------------|
| `src/erk/cli/commands/wt/create_cmd.py:996, 1006` | `erk wt create --stay` | Prints instructions (optional) |
| `src/erk/cli/commands/wt/checkout_cmd.py:123` | `erk wt checkout WORKTREE` | Prints instructions |
| `src/erk/cli/commands/wt/create_from_cmd.py:109` | `erk wt create-from BRANCH` | Prints instructions |
| `src/erk/cli/commands/branch/checkout_cmd.py:250` | `erk br checkout BRANCH` | Prints instructions |
| `src/erk/cli/commands/branch/create_cmd.py` | `erk br create` | Prints instructions |
| `src/erk/cli/commands/pr/checkout_cmd.py:237, 328` | `erk pr checkout` | Prints instructions (2 instances) |
| `src/erk/cli/commands/navigation_helpers.py:394, 855` | Core navigation | Prints instructions (2 instances) |
| `src/erk/cli/commands/land_cmd.py:1095` | `erk pr land` | Prints temp script instructions |

**Special case**: `erk br co --for-plan` with stack-in-place (checkout_cmd.py:598-651)
- Currently returns early from `_branch_checkout_impl()` and calls `_perform_checkout()` with unmodified `script` parameter
- Should treat stack-in-place like script mode to enable auto-execution

## Implementation Strategy

### Phase 1: Unify script output for stack-in-place (HIGH PRIORITY)
**Scope**: `src/erk/cli/commands/branch/checkout_cmd.py`

When stacking in place (`current_assignment is not None`):
1. Add `force_script_activation: bool = False` parameter to `_perform_checkout()`
2. In `_perform_checkout()`, treat `force_script_activation or script` as effective script mode
3. In stack-in-place branch (line 643), pass `force_script_activation=True`
4. When effective script mode is True, output activation script path instead of printing instructions

### Phase 2: Extend to other checkout commands (MEDIUM PRIORITY)
**Scope**: `erk wt checkout`, `erk wt create-from`, `erk br checkout`

Apply same pattern:
1. Add `force_script_activation` parameter to shared navigation functions
2. In `navigate_to_worktree()`, detect cases where auto-execution is beneficial
3. Refactor `print_activation_instructions()` to be called only when interactive output is truly needed

### Phase 3: Standardize across all interactive navigation (LOWER PRIORITY)
**Scope**: Core navigation helpers and edge cases

Clean up:
1. Review `src/erk/cli/commands/navigation_helpers.py` for unified pattern
2. Consider making script output the default when not explicitly in interactive mode
3. Add configuration flag for users who prefer explicit instructions

## Critical Files to Modify

- **`src/erk/cli/commands/branch/checkout_cmd.py`** (Phase 1)
  - Lines 160-256: `_perform_checkout()` function
  - Lines 598-651: `_branch_checkout_impl()` stack-in-place branch

- **`src/erk/cli/commands/checkout_helpers.py`** (Phase 1)
  - Lines 168-216: `navigate_to_worktree()` function

- **`src/erk/cli/activation.py`** (Phase 1-2)
  - Functions that control script vs interactive output

- **Other checkout commands** (Phase 2)
  - `src/erk/cli/commands/wt/checkout_cmd.py`
  - `src/erk/cli/commands/wt/create_from_cmd.py`
  - `src/erk/cli/commands/branch/create_cmd.py`

## Implementation Plan (Phase 1 - Stack in Place)

### Step 1: Add parameter to `_perform_checkout()`
```python
def _perform_checkout(
    ctx: ErkContext,
    repo_root: Path,
    target_worktree: WorktreeInfo,
    branch: str,
    script: bool,
    is_newly_created: bool,
    worktrees: Sequence[WorktreeInfo],
    force_script_activation: bool = False,  # NEW
) -> None:
```

### Step 2: Modify navigate_to_worktree() call
```python
effective_script = script or force_script_activation  # NEW
should_output_message = navigate_to_worktree(
    ctx,
    worktree_path=target_path,
    branch=branch,
    script=effective_script,  # Use effective_script
    ...
)
```

### Step 3: Update stack-in-place call
```python
_perform_checkout(
    ctx,
    repo_root=repo.root,
    target_worktree=target_wt,
    branch=branch,
    script=script,
    is_newly_created=False,
    worktrees=worktrees,
    force_script_activation=True,  # Force script mode
)
```

## Testing & Verification

### Test Cases - Phase 1

1. **Stack in place with plan** (from assigned slot):
   ```bash
   erk br co --for-plan <number>
   # Expect: Activation script output (no interactive prompt)
   ```

2. **Stack in place without plan** (from assigned slot):
   ```bash
   erk br co <branch>
   # Expect: Activation script output (no interactive prompt)
   ```

3. **New slot allocation**:
   ```bash
   erk br co --new-slot <branch>  # or from root worktree
   # Expect: Keep existing behavior (interactive prompt)
   ```

4. **Shell integration compatibility**:
   - Verify `source "$(erk br co --script)"` still works
   - Verify stack-in-place auto-execution works with shell integration enabled

## Acceptance Criteria

- ✅ Stack-in-place cases output activation script instead of interactive prompt
- ✅ Shell integration wrapper still functions correctly
- ✅ New slot allocation preserves existing behavior
- ✅ All existing tests pass
- ✅ Code changes are minimal and focused on Phase 1
- ✅ Future phases documented for follow-up work
