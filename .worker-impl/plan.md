# Plan: Add git pull to /erk:submit-plan

## Goal

Enhance `/erk:submit-plan` to attempt `git pull` before running `erk submit` when:

1. Current branch is master (or the trunk branch)
2. Working directory is clean (no uncommitted changes)

## Implementation

### File to Modify

`/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/submit-plan.md`

### Changes

Add a new section between "Finding the Issue" and "Execution" called "Pre-Execution: Sync Trunk". This section will instruct the agent to:

1. Get the current branch: `git branch --show-current`
2. Get the trunk branch name: `git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'` (or use `git remote show origin | grep 'HEAD branch'`)
3. Check if on trunk (current branch equals trunk branch)
4. If on trunk, check if working directory is clean: `git status --porcelain`
5. If both conditions are met, run: `git pull --ff-only`
6. Report success/skip reason to user

### Updated Command Structure

```markdown
## Goal

(unchanged)

## What This Command Does

1. Search conversation for the last GitHub issue reference
2. Extract the issue number
3. **Sync trunk if on master/main with clean working directory** (NEW)
4. Run `erk submit <issue_number>` to trigger remote implementation

## Finding the Issue

(unchanged)

## Pre-Execution: Sync Trunk (NEW SECTION)

Before running `erk submit`, check if trunk should be synced:

1. Get the current branch and trunk branch name
2. If current branch is the trunk branch (master or main):
   - Check if working directory is clean (no uncommitted changes)
   - If clean, run `git pull --ff-only` to sync with remote
   - Report: "Syncing trunk before submit..." / "Trunk synced."
3. If not on trunk or working directory is dirty, skip this step silently

## Execution

(unchanged)

## Error Cases

(add new case)

- **git pull fails**: Report the error but continue with `erk submit` anyway (pull failure shouldn't block submit)
```

### Key Design Decisions

1. **Use `--ff-only`**: Prevents merge commits if local has diverged; fails cleanly
2. **Non-blocking on pull failure**: If pull fails, continue with submit (the purpose is to get latest, not to block the workflow)
3. **Silent skip when not applicable**: Don't clutter output when not on trunk or dirty
4. **Trunk detection**: Use git to detect trunk branch name dynamically (supports both `main` and `master`)
