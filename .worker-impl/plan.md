---
steps:
  - name: "Fix test_plan_saved_marker_flow flakiness"
  - name: "Fix test_plan_save_to_issue_session_id_still_creates_marker flakiness"
  - name: "Run make fast-ci to verify fixes"
---

# Fix Flaky Tests in test_exit_plan_mode_hook.py and test_plan_save_to_issue.py

## Problem Analysis

Two tests are flaky when running with pytest-xdist (parallel execution):

1. **`test_plan_saved_marker_flow`** (exit_plan_mode_hook.py:320)
   - Expected: exit code 2 (BLOCK)
   - Got: exit code 1 (exception)

2. **`test_plan_save_to_issue_session_id_still_creates_marker`** (plan_save_to_issue.py:370)
   - Expected: exit code 0
   - Got: FileNotFoundError

Both tests pass individually but fail intermittently in parallel execution.

## Root Cause

The production code reaches outside the test's injected context to read from the real home directory:

### For `exit_plan_mode_hook.py`:
- `_is_github_planning_enabled()` reads `Path.home() / ".erk" / "config.toml"`
- `_find_session_plan()` calls `extract_slugs_from_session()` which reads `Path.home() / ".claude" / projects/`
- `_get_current_branch_within_hook()` runs `git rev-parse --abbrev-ref HEAD` via subprocess

### For `plan_save_to_issue.py`:
- Line 278: `extract_slugs_from_session()` reads from real `~/.claude/projects/`
- This can fail or return unexpected data if the real home directory is modified by concurrent Claude Code sessions

## Fix Approach

**For `test_plan_saved_marker_flow`**: The test creates a plan-saved marker, so the hook should return BLOCK (exit code 2) without needing to call `_find_session_plan()` or other I/O. The issue is that `_is_github_planning_enabled()` is called first and reads the real home directory. If there's an issue reading/parsing the config, it could throw an exception (exit code 1).

**Fix**: Mock or inject the github_planning_enabled flag, OR ensure the test doesn't depend on real filesystem state.

However, looking more carefully at the test:
- It creates `.erk/` in tmp_path
- It creates the marker file
- It passes `ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)`

But `_is_github_planning_enabled()` is NOT injected - it reads from `Path.home()`. This is the bug.

**Solution**: The tests should not be testing I/O code paths that read from the real home directory. The tests should:
1. Either mock `_is_github_planning_enabled()` to return True
2. Or refactor the code to use dependency injection for the github_planning flag

Given the project's preference for dependency injection over mocking, we should:
1. Add a `github_planning_enabled` parameter to `HookContext` that can be injected in tests
2. Have `_gather_inputs()` use this injected value when available

## Implementation Plan

### Step 1: Fix test_plan_saved_marker_flow

The simplest fix is to ensure the test doesn't hit real filesystem paths. Options:
1. **Option A**: Use monkeypatch to set `_is_github_planning_enabled` return value
2. **Option B**: Add environment variable or test mode to disable home directory reads
3. **Option C**: Refactor HookContext to accept github_planning_enabled as optional override

Given the existing pattern of using `ErkContext.for_test()`, Option C is most consistent.

However, for a quick fix that doesn't require refactoring production code, we can use `monkeypatch` in the test to patch `_is_github_planning_enabled` to return True.

### Step 2: Fix test_plan_save_to_issue_session_id_still_creates_marker

Similarly, this test should not rely on `extract_slugs_from_session()` hitting the real filesystem. Since the test already uses `FakeClaudeCodeSessionStore`, the issue is that the plan_save_to_issue code calls `extract_slugs_from_session()` directly (not through the fake).

Looking at lines 273-290 in plan_save_to_issue.py:
- The snapshot logic is optional and only runs when certain conditions are met
- We can add a guard or make the test more robust

Actually, re-reading the error: `FileNotFoundError` - this could come from `runner.isolated_filesystem()` interacting badly with the current working directory during parallel execution.

The fix is to ensure the test doesn't depend on real filesystem state. We can use `monkeypatch` to patch the problematic functions.

## Files to Modify

1. `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`
   - Add monkeypatch for `_is_github_planning_enabled` in `test_plan_saved_marker_flow`

2. `tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py`
   - Add monkeypatch for `extract_slugs_from_session` in `test_plan_save_to_issue_session_id_still_creates_marker`

## Verification

Run `make fast-ci` to verify all tests pass including in parallel mode.