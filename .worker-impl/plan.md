# Implementation Plan: Phase 5 - Activation Output for Create Commands

**Part of Objective #4954, Phase 5 (Steps 5.1 and 5.2)**

## Goal

Add activation script output to `erk wt create` and `erk pr checkout` commands. After creating or navigating to a worktree, both commands will print:

```
To activate the worktree environment:
  source /path/to/worktree/.erk/activate.sh

To activate and start implementation:
  source /path/to/worktree/.erk/activate.sh && erk implement --here
```

This makes the opt-in shell integration workflow visible to users and establishes the pattern for remaining phases (navigation commands, land command).

## Design Context

From objective exploration:

- **Foundation exists**: Phase 2 added `ensure_worktree_activate_script()` helper (PR #4982)
- **Pattern established**: Phase 3 (`erk br create --for-plan`) already prints activation paths (PR #5042, #5046)
- **Gap identified**: `erk wt create` writes activation scripts but doesn't print the path; `erk pr checkout` neither writes nor prints

## Current State Analysis

**`erk wt create` (src/erk/cli/commands/wt/create_cmd.py)**:
- Already calls `write_worktree_activate_script()` when `ENABLE_ACTIVATION_SCRIPTS = True` (lines 58-62, 866-871)
- Missing: Print the activation path after creation
- Location: After worktree creation, before navigation

**`erk pr checkout` (src/erk/cli/commands/pr/checkout_cmd.py)**:
- Uses `ensure_branch_has_worktree()` to create worktrees (line 116-118)
- Missing: Both script creation AND path printing
- Challenge: Shared helper `ensure_branch_has_worktree()` doesn't call `run_post_worktree_setup()`

**Pattern to follow** (from `erk br create --for-plan`, lines 157-169):
```python
script_path = write_worktree_activate_script(
    worktree_path=slot_result.worktree_path,
    post_create_commands=None,
)

user_output("\nTo activate the worktree environment:")
user_output(f"  source {script_path}")

user_output("\nTo activate and start implementation:")
user_output(f"  source {script_path} && erk implement --here")
```

## Implementation Phases

### Phase 1: Add Activation Output to `erk wt create`

**File**: `src/erk/cli/commands/wt/create_cmd.py`

**Changes**:

1. After calling `write_worktree_activate_script()`, capture the returned path
2. Add activation output helper function (reusable for both commands):
   ```python
   def print_activation_instructions(script_path: Path) -> None:
       """Print activation script instructions."""
       user_output("\nTo activate the worktree environment:")
       user_output(f"  source {script_path}")

       user_output("\nTo activate and start implementation:")
       user_output(f"  source {script_path} && erk implement --here")
   ```
3. Call `print_activation_instructions()` after worktree creation (two call sites: lines ~62 and ~871)

**Key decision**: Use the path already returned by `write_worktree_activate_script()` - no need to call `ensure_worktree_activate_script()` again.

**Files to modify**:
- `src/erk/cli/commands/wt/create_cmd.py` (add helper, call after script creation)

**Tests to update**:
- `tests/unit/cli/commands/wt/test_create_cmd.py` - verify output contains activation instructions

### Phase 2: Add Activation Scripts to `ensure_branch_has_worktree()`

**File**: `src/erk/cli/commands/checkout_helpers.py`

**Problem**: The shared helper `ensure_branch_has_worktree()` creates worktrees but doesn't write activation scripts.

**Solution**: After creating a new worktree (when `already_existed = False`), call `ensure_worktree_activate_script()`.

**Changes**:

1. Import `ensure_worktree_activate_script` from `erk.cli.activation`
2. After worktree creation (lines 197-215), before return:
   ```python
   # Write activation script for new worktrees
   if ENABLE_ACTIVATION_SCRIPTS:
       from erk.cli.activation import ensure_worktree_activate_script
       ensure_worktree_activate_script(
           worktree_path=worktree_path,
           post_create_commands=None,
       )
   ```
3. Import `ENABLE_ACTIVATION_SCRIPTS` from `erk.cli.activation`

**Why `ensure_` not `write_`**: This helper is used by multiple commands. Some may already have scripts (e.g., pool slots), so we use the idempotent version.

**Files to modify**:
- `src/erk/cli/commands/checkout_helpers.py` (add activation script creation)

**Tests to update**:
- `tests/unit/cli/commands/test_checkout_helpers.py` - verify activation script exists after creation

### Phase 3: Add Activation Output to `erk pr checkout`

**File**: `src/erk/cli/commands/pr/checkout_cmd.py`

**Changes**:

1. After `navigate_and_display_checkout()` call (line 144-155), ensure activation script exists and print path:
   ```python
   # Print activation instructions (only if script mode is off)
   if not script and ENABLE_ACTIVATION_SCRIPTS:
       from erk.cli.activation import ensure_worktree_activate_script
       from erk.cli.commands.wt.create_cmd import print_activation_instructions

       script_path = ensure_worktree_activate_script(
           worktree_path=worktree_path,
           post_create_commands=None,
       )
       print_activation_instructions(script_path)
   ```

2. Import `ENABLE_ACTIVATION_SCRIPTS` from `erk.cli.activation`

**Why after navigation?**: The `navigate_and_display_checkout()` helper prints sync status. Activation instructions should come last.

**Why check `script` mode?**: In script mode, shell integration handles navigation automatically. Only print instructions in non-script mode.

**Files to modify**:
- `src/erk/cli/commands/pr/checkout_cmd.py` (add activation output after navigation)

**Tests to update**:
- `tests/unit/cli/commands/pr/test_checkout_cmd.py` - verify output contains activation instructions (non-script mode only)

### Phase 4: Extract Shared Helper

**File**: Create `src/erk/cli/activation_output.py` (or add to existing `activation.py`)

**Rationale**: Both `erk wt create` and `erk pr checkout` need the same output helper. Extract to avoid duplication.

**Changes**:

1. Move `print_activation_instructions()` to `erk.cli.activation` module
2. Update imports in both `wt/create_cmd.py` and `pr/checkout_cmd.py`

**Alternative**: Keep helper in `wt/create_cmd.py` and import from there. This avoids adding to the already-large `activation.py` module.

**Decision**: Start with helper in `wt/create_cmd.py`. If other commands need it (Phase 6: navigation commands), extract to `activation.py`.

**Files to modify** (deferred to Phase 6 if needed):
- None for this phase

## Verification

**Manual testing**:

1. **Test `erk wt create`**:
   ```bash
   erk wt create test-branch-wt
   # Should print activation instructions with path to .erk/activate.sh
   ```

2. **Test `erk pr checkout`** (existing PR):
   ```bash
   erk pr checkout 123
   # Should print activation instructions after creation/navigation
   ```

3. **Verify activation script works**:
   ```bash
   source /path/to/worktree/.erk/activate.sh
   # Should cd to worktree, activate venv, load .env
   ```

4. **Test combined command**:
   ```bash
   source /path/to/worktree/.erk/activate.sh && erk implement --here
   # Should activate and start implementation in same shell
   ```

**Automated tests**:
- Unit tests verify output contains "To activate the worktree environment:"
- Unit tests verify output contains "source .erk/activate.sh"
- Unit tests verify activation script file exists at expected path
- Tests verify script mode doesn't print activation instructions (shell integration handles it)

## Critical Files

**To modify**:
- `src/erk/cli/commands/wt/create_cmd.py` (add output after script creation)
- `src/erk/cli/commands/checkout_helpers.py` (add script creation to `ensure_branch_has_worktree`)
- `src/erk/cli/commands/pr/checkout_cmd.py` (add output after navigation)

**To read for patterns**:
- `src/erk/cli/commands/branch/create_cmd.py` (Phase 3 reference: lines 157-169)
- `src/erk/cli/activation.py` (helper functions)
- `tests/unit/cli/commands/branch/test_create_cmd.py` (output assertions)

**Test files**:
- `tests/unit/cli/commands/wt/test_create_cmd.py`
- `tests/unit/cli/commands/pr/test_checkout_cmd.py`
- `tests/unit/cli/commands/test_checkout_helpers.py`

## Edge Cases

1. **Activation script already exists**: Use `ensure_worktree_activate_script()` (idempotent) for `pr checkout`
2. **Script mode enabled**: Skip printing instructions (shell integration handles it)
3. **Worktree already existed**: Still print activation instructions (user may want to re-activate)
4. **ENABLE_ACTIVATION_SCRIPTS = False**: Skip both script creation and output (feature flag)

## Success Criteria

- ✅ `erk wt create` prints activation path after creating worktree
- ✅ `erk pr checkout` prints activation path after creating/navigating to worktree
- ✅ Activation scripts exist at `.erk/activate.sh` for both commands
- ✅ Output format matches Phase 3 pattern (two sections: standalone + combined)
- ✅ Script mode doesn't print instructions (shell integration handles it)
- ✅ Tests verify output and script existence
- ✅ Feature flag `ENABLE_ACTIVATION_SCRIPTS` gates both creation and output

## Related Documentation

**Skills loaded**:
- `dignified-python` - Python coding standards
- `fake-driven-testing` - Test architecture and patterns
- `objective` - Objective format and workflow

**Docs referenced**:
- `docs/learned/cli/` - CLI command patterns
- `docs/learned/testing/` - Test placement and structure
- Objective #4954 - Parent objective for shell integration opt-in