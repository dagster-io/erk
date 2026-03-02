# Add "Implement on current branch" option to exit plan mode hook

## Context

When exiting plan mode, the hook presents 3 options: save as plan PR, skip PR and implement (which creates a new branch via `setup-impl`), or view/edit the plan. There's no option to implement directly on the current branch without creating a new branch. This is needed for cases where the branch was already created by another tool (e.g., `erk wt create`, manual branch creation).

## Changes

### 1. Modify `build_blocking_message()` in `exit_plan_mode_hook.py`

**File:** `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py`

Add a new option 3 "Implement on current branch" and shift "View/Edit" to option 4. This gives exactly 4 options (AskUserQuestion max). Also clarify option 2's description to note it creates a new branch.

**Option list becomes:**
```
1. "Create a plan PR" (Recommended) - Create a draft PR with the plan and stop.
2. "New branch and implement" - Create a new branch in the current worktree and implement (for starting fresh).
3. "Implement on current branch" - Implement directly on the current branch without creating a new branch or worktree.
4. "View/Edit the plan" - Open plan in editor to review or modify before deciding.
```

**Add instruction block for option 3:**
```
If user chooses 'Implement on current branch':
  1. Create implement-now marker:
     erk exec marker create --session-id {session_id} \
       exit-plan-mode-hook.implement-now
  2. Call ExitPlanMode
  3. After exiting plan mode, implement the changes directly on the current branch.
     Do NOT run 'erk exec setup-impl' or create a new branch.
     Read the plan from: {plan_file_path}
     Implement changes, run CI, and optionally 'erk pr submit' when done.
```

The new option reuses the existing `implement-now` marker - no new marker type needed. The difference from option 2 is purely in the agent instructions after ExitPlanMode (no `setup-impl`, no branch creation).

**Also update option 2's instruction block label** from `'Skip PR and implement here'` to match the new label.

### 2. Update tests

**File:** `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`

Update `TestBuildBlockingMessage` tests that assert on message content:

- `test_contains_required_elements`: Update assertions for renamed option 2 and add assertions for new option 3 ("Implement on current branch")
- `test_draft_pr_backend_instruction_blocks`: Update instruction block label assertions
- Add new test `test_implement_on_current_branch_option_included`: Verify the new option text and instruction block appear in the message
- Update `test_edit_plan_instructions_include_path`: The "loop until" text may reference the new option name

No changes needed to `TestDetermineExitAction` - the pure logic uses the same `implement-now` marker for both options 2 and 3.

## Verification

1. Run unit tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`
2. Run ty type checking on the modified file
3. Manually test: enter plan mode, create a plan, call ExitPlanMode, verify 4 options appear
