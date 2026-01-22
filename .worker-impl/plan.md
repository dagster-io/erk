# Plan: Implement `erk pr summarize` command

## Overview

Create a new CLI command `erk pr summarize` that generates an AI-powered commit message and amends the current commit. This is a subset of `erk pr submit` focused only on local commit message generation.

## Requirements

1. Only works when there's exactly 1 commit on the branch (compared to Graphite parent)
2. If multiple commits exist, error with instruction to run `gt squash`
3. When single commit exists:
   - Get diff between current branch and parent branch
   - Use Claude to generate commit message (title + body)
   - Amend the commit with the AI-generated message

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/erk/cli/commands/pr/summarize_cmd.py` | Create |
| `src/erk/cli/commands/pr/__init__.py` | Add import and registration |
| `tests/commands/pr/test_summarize.py` | Create tests |

## Implementation

### Command Logic (`summarize_cmd.py`)

```
1. Verify Claude CLI available
2. Get current branch (fail if detached HEAD)
3. Get parent branch (Graphite-aware, falls back to trunk)
4. Count commits ahead of parent:
   - 0 commits → error: "Make a commit first"
   - >1 commits → error: "Run gt squash first"
   - 1 commit → proceed
5. Get diff to parent branch
6. Filter lock files + truncate if needed
7. Write diff to scratch file
8. Generate commit message via CommitMessageGenerator
9. Amend commit with new message
10. Show success with title preview
```

### Reused Components

- `ctx.branch_manager.get_parent_branch()` - Graphite-aware parent lookup
- `ctx.git.count_commits_ahead()` - commit count check
- `ctx.git.get_diff_to_branch()` - local diff generation
- `filter_diff_excluded_files()` - remove lock files from diff
- `truncate_diff()` - handle large diffs
- `write_scratch_file()` - session-scoped diff storage
- `CommitMessageGenerator` - AI message generation
- `ctx.git.amend_commit()` - apply new message

### Command Registration

Add to `pr/__init__.py`:
```python
from erk.cli.commands.pr.summarize_cmd import pr_summarize
# ...
pr_group.add_command(pr_summarize, name="summarize")
```

## Test Cases

1. Fail when Claude not available
2. Fail when no commits ahead of parent
3. Fail when multiple commits (with `gt squash` instruction)
4. Success with single commit - verify amend called
5. Uses Graphite parent branch when available

## Verification

```bash
# Create test branch with single commit
gt create -m "test" test-summarize
echo "test" > test.txt && git add . && git commit -m "WIP"

# Run the command
erk pr summarize

# Verify commit message was updated
git log -1 --format=%B
```

## Related Documentation

- `dignified-python` skill for coding standards
- `fake-driven-testing` skill for test patterns