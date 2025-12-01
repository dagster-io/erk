# Fix: erk planner connect - claude command not found in non-interactive SSH

## Problem

When running `erk planner connect`, the command fails with:
```
bash: line 1: claude: command not found
```

The current implementation runs:
```python
os.execvp("gh", ["gh", "codespace", "ssh", "-c", planner.gh_name, "--", "claude"])
```

When `gh codespace ssh` is invoked with a command after `--`, it executes in a **non-interactive shell** that doesn't source profile files (`.bashrc`, `.zshrc`). Since Claude Code installs to `~/.claude/local/` and adds itself to PATH via shell profiles, the `claude` command isn't found.

## Solution

Use `bash -l -c claude` to invoke a **login shell** that sources profile files before executing `claude`.

## Implementation

### 1. Update `connect_cmd.py`

**File:** `src/erk/cli/commands/planner/connect_cmd.py`

Change line 53 from:
```python
os.execvp("gh", ["gh", "codespace", "ssh", "-c", planner.gh_name, "--", "claude"])
```

To:
```python
os.execvp("gh", ["gh", "codespace", "ssh", "-c", planner.gh_name, "--", "bash", "-l", "-c", "claude"])
```

Add a comment explaining why:
```python
# Use bash login shell to ensure PATH is set up (claude installs to ~/.claude/local/)
```

### 2. Update test assertions

**File:** `tests/commands/planner/test_planner_connect.py`

Update `test_connect_executes_claude_command()` to verify the new command structure:
- Check that the args include `"bash"`, `"-l"`, `"-c"`, and `"claude"`
- The current assertion `assert "claude" in args_list` will still pass but should be made more specific

## Files to Modify

1. `src/erk/cli/commands/planner/connect_cmd.py` - Fix the SSH command
2. `tests/commands/planner/test_planner_connect.py` - Update test assertions