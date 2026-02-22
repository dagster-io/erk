---
title: Remote Branch Learn Support
read_when:
  - "modifying learn workflow branch checks"
  - "understanding why learn runs for non-current branches"
  - "debugging learn status prompts on landing"
tripwires:
  - action: "adding redundant branch-location guards to learn status checks"
    warning: "Learn status checking in land_pipeline.py:341 requires is_current_branch or worktree_path is not None. Remote branches (is_current_branch=False, worktree_path=None) are not prompted for learn — this is intentional since remote sessions are handled via async-learn branches."
---

# Remote Branch Learn Support

The learn workflow's `check_learn_status()` in the land pipeline only prompts for learn when the branch is locally accessible: `is_current_branch or worktree_path is not None` (land_pipeline.py:341). Remote plan branches skip the interactive learn prompt.

## Branch-Location Guard Behavior

Remote plan branches (implemented by CI workers) have:

- `is_current_branch = False` (not checked out locally)
- `worktree_path = None` (no local worktree)

The guard at land_pipeline.py:341 skips the interactive learn prompt for these branches. This is intentional — remote sessions are uploaded to `async-learn/{plan_id}` branches by the CI worker and don't need interactive prompting during land.

## Session Discovery for Remote Branches

<!-- Source: src/erk/cli/commands/land_pipeline.py, check_learn_status -->

`check_learn_status()` in the land pipeline resolves the plan ID from the branch name. If the branch is locally accessible (current branch or has a worktree), it delegates to `_check_learn_status_and_prompt()` for interactive learn prompting.

Session data for remote branches is discovered via plan metadata fields:

- `last_session_branch` — git branch containing the session JSONL
- `last_session_id` — Claude Code session ID

## Built-in Safety

`_check_learn_status_and_prompt()` has its own guards that don't depend on branch location:

- Skips if learn is already completed
- Skips in CI environments (auto-select)
- Respects force flags and script mode

## Code Location

<!-- Source: src/erk/cli/commands/land_pipeline.py -->

`src/erk/cli/commands/land_pipeline.py` — `check_learn_status()` function, lines ~332-350.
