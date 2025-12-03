# Plan: Add Squash to Auto-Restack

## Goal

Add squash functionality to `erk pr auto-restack` so the restacked branch ends up with a single commit. Include `--no-squash` flag to opt-out.

## Current Behavior

1. CLI (`auto_restack_cmd.py`) delegates to Claude slash command (`/erk:auto-restack`)
2. Slash command runs `gt restack --no-interactive` and handles conflicts
3. Result: branch is restacked but may have multiple commits

## Desired Behavior

After restack completes, squash all commits into one (unless `--no-squash` is passed).

---

## Implementation

### Step 1: Update CLI Command

**File:** `src/erk/cli/commands/pr/auto_restack_cmd.py`

Add `--no-squash` flag and pass it via the command string:

```python
@click.command("auto-restack")
@click.option(
    "--no-squash",
    is_flag=True,
    help="Skip squashing commits after restack.",
)
@click.pass_obj
def pr_auto_restack(ctx: ErkContext, no_squash: bool) -> None:
    """Restack with AI-powered conflict resolution.

    Runs `gt restack` and automatically handles any merge conflicts that arise,
    looping until the restack completes successfully. After restacking, squashes
    all commits into a single commit (use --no-squash to skip).
    ...
    """
    # ... existing code ...

    # Build command with optional --no-squash flag
    command = "/erk:auto-restack"
    if no_squash:
        command = "/erk:auto-restack --no-squash"

    for event in executor.execute_command_streaming(
        command=command,  # Changed from hardcoded string
        worktree_path=worktree_path,
        dangerous=True,
    ):
```

### Step 2: Update Slash Command

**File:** `.claude/commands/erk/auto-restack.md`

Add argument parsing and squash step. Changes needed:

**A. Add Arguments section at top:**

```markdown
## Arguments

- `--no-squash` - Skip the squash step after restacking (keep multiple commits)
```

**B. Add Step 4.5 after successful restack completion (before Step 5):**

```markdown
### Step 4.5: Squash Commits (default behavior)

After the restack completes successfully and BEFORE verifying completion:

1. **Check if squash was disabled** - If `--no-squash` was passed, skip to Step 5
2. **Count branch commits**:

\`\`\`bash
git rev-list --count HEAD ^$(gt parent)
\`\`\`

3. **Squash if 2+ commits** - If count >= 2, run:

\`\`\`bash
gt squash --no-edit
\`\`\`

4. **Handle squash conflicts** - If squash fails with conflicts:
   - Apply the same conflict resolution logic from Step 3
   - After resolving, continue with `git rebase --continue`
   - Repeat until squash completes
```

### Step 3: Update Tests

**File:** `tests/commands/pr/test_auto_restack.py`

Add two new tests:

```python
def test_pr_auto_restack_passes_no_squash_flag() -> None:
    """Test that --no-squash flag is passed to slash command."""
    # Verify the command includes --no-squash
    command, _, _, _ = claude_executor.executed_commands[0]
    assert command == "/erk:auto-restack --no-squash"


def test_pr_auto_restack_squashes_by_default() -> None:
    """Test that squash is NOT skipped by default (no --no-squash flag)."""
    # Verify no --no-squash flag in command
    command, _, _, _ = claude_executor.executed_commands[0]
    assert command == "/erk:auto-restack"
    assert "--no-squash" not in command
```

---

## Files to Modify

| File                                          | Changes                                                                      |
| --------------------------------------------- | ---------------------------------------------------------------------------- |
| `src/erk/cli/commands/pr/auto_restack_cmd.py` | Add `--no-squash` flag, update docstring, conditionally build command string |
| `.claude/commands/erk/auto-restack.md`        | Add Arguments section, add Step 4.5 for squash                               |
| `tests/commands/pr/test_auto_restack.py`      | Add 2 tests for flag behavior                                                |

---

## Summary

The implementation is straightforward:

1. CLI adds `--no-squash` flag -> appends to command string
2. Slash command parses argument -> skips squash step if present
3. Default behavior: squash after restack completes
