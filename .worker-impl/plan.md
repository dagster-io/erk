# Plan: Replace "Switched to" with "Went to" in User-Facing Messages

## Summary

Replace all "Switched to" / "Switching to" language in user-facing messages with "Went to" / "Going to" to align with the `goto` command naming convention.

## Files to Modify

### 1. src/erk/cli/commands/wt/goto_cmd.py

**Line 91** - User message:

```python
# FROM:
user_output(f"Switched to worktree {styled_wt} [{styled_branch}]")
# TO:
user_output(f"Went to worktree {styled_wt} [{styled_branch}]")
```

**Lines 20, 34, 37, 69** - Help text and docstrings:

- Line 20: "Switch directly to a worktree" → "Go directly to a worktree"
- Line 34: "# Switch to the root repository" → "# Go to the root repository"
- Line 37: "# Switch to worktree named" → "# Go to worktree named"
- Line 69: "'erk checkout' to switch by branch name" → "'erk checkout' to go by branch name"

### 2. src/erk/cli/commands/checkout.py

**Lines 178-235** - User messages (both script mode and dry-run):

- "Switched to new worktree" → "Went to new worktree"
- "Switched to worktree {name}" → "Went to worktree {name}"
- "Switched to worktree {name} (branch {branch})" → "Went to worktree {name} (branch {branch})"
- "Switched to worktree {name} and checked out branch {branch}" → "Went to worktree {name} and checked out branch {branch}"

**Lines 1, 250, 253** - Docstrings:

- Line 1: "find and switch to a worktree" → "find and go to a worktree"
- Line 250: "switching to its worktree" → "going to its worktree"
- Line 253: "switches to it" → "goes to it"

### 3. src/erk/cli/commands/wt/create_cmd.py

**Line 922** - User message:

```python
# FROM:
success_message="✓ Switched to new worktree.",
# TO:
success_message="✓ Went to new worktree.",
```

**Lines 105, 179, 245, 506, 715, 775, 805** - Help text:

- "To switch to {branch}" → "To go to {branch}"
- "Switch to existing worktree" → "Go to existing worktree"
- "Switch to that worktree" → "Go to that worktree"
- "instead of switching to new worktree" → "instead of going to new worktree"
- "Switch to a feature branch first" → "Go to a feature branch first"

**Line 480** - Help text for --from-current-branch:

- "then switch current worktree to --ref" → rephrase for clarity with "go"

### 4. src/erk/cli/commands/pr/land_cmd.py

**Lines 117, 127** - User messages:

- "Landed PR and switched to trunk" → "Landed PR and went to trunk"
- "Switched to: {dest_path}" → "Went to: {dest_path}"

### 5. src/erk/cli/commands/pr/checkout_cmd.py

**Line 81** - User message:

```python
# FROM:
final_message=f'echo "Switched to existing worktree for PR #{pr_number}"',
# TO:
final_message=f'echo "Went to existing worktree for PR #{pr_number}"',
```

### 6. src/erk/cli/commands/down.py

**Lines 91, 101** - User messages:

- "Switched to root repo" → "Went to root repo"

### 7. src/erk/cli/commands/stack/consolidate_cmd.py

**Lines 211, 400, 411, 412** - User messages and help:

- "Switch to existing" → "Go to existing"
- "✓ Switched to consolidated worktree." → "✓ Went to consolidated worktree."
- "Switching to worktree" → "Going to worktree"
- "Run this command to switch" → "Run this command to go there"

### 8. src/erk/cli/commands/navigation_helpers.py

**Lines 105, 115** - User messages:

- "Switched to root repo" → "Went to root repo"

### 9. Tests to Update

**tests/commands/navigation/test_checkout.py** - Update assertions:

- Lines checking for "Switched to new worktree" → "Went to new worktree"
- Lines checking for "Switched to worktree" → "Went to worktree"

**tests/commands/navigation/test_checkout_messages.py** - Update test names and assertions:

- Rename tests with "switched" in name to use "went_to"
- Update all message assertions

**tests/commands/management/test_impl.py** - Update assertions:

- Line 365, 370: "Switched to new worktree" → "Went to new worktree"

## NOT Changing

- Internal variable names (`switch_message`, `is_switching_location`, `try_switch_root_worktree`)
- Industry standard terms ("context switching", "branch switching" when describing the problem)
- External CLI references ("gh auth switch")
- Shell wrapper comments (describe the concept, not UI messages)
- Documentation that describes the problem space (README.md, TAO.md references to "branch switching")

## Implementation Order

1. Update source files (commands)
2. Update test files (assertions and test names)
3. Run tests to verify
4. Run pyright for type checking
