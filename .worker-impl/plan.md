# Plan: Fix .worker-impl/ appearing in commit summaries

## Objective

Fix the `/erk:plan-implement` command so that `.worker-impl/` files don't appear in commit messages and PR bodies.

## Problem

When an implementation runs in a `.worker-impl/` folder:
1. Implementation changes are staged (including any changes to `.worker-impl/progress.md`)
2. A commit is created with a message generated from `git diff --staged`
3. The diff analysis includes `.worker-impl/` files in the summary
4. Then `.worker-impl/` is deleted in a separate commit
5. The PR body (derived from commit message) still references `.worker-impl/`

Evidence from PR #1803: The commit message and PR body mention `.worker-impl/plan.md` even though the final PR doesn't include that file.

## Solution

Modify Step 9 in `plan-implement.md` to:
1. Delete `.worker-impl/` folder FIRST
2. Stage all changes (both implementation + `.worker-impl/` deletion)
3. THEN generate the commit message from staged diff
4. Create a single atomic commit

This ensures the diff analysis never sees `.worker-impl/` files.

## Implementation Steps

### Step 1: Update Step 9 in plan-implement.md

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-implement.md`

**Current flow (lines 337-344):**
```markdown
**After CI passes (or if .impl/ folder):**

If in .worker-impl/ folder:

1. Delete .worker-impl/ folder: `rm -rf .worker-impl/`
2. Stage deletion: `git add .worker-impl/`
3. Commit: `git commit -m "Clean up worker implementation artifacts after implementation"`
4. Push: `git push`
```

**New flow:**
```markdown
**After CI passes:**

If in .worker-impl/ folder:

1. Delete .worker-impl/ folder FIRST: `rm -rf .worker-impl/`
2. Stage ALL changes (implementation + folder deletion): `git add -A`
3. Get the staged diff for commit message generation: `git diff --staged`
4. Generate commit message from the diff (following diff-analysis-guide.md)
   - **IMPORTANT:** The diff now correctly excludes .worker-impl/ files
5. Create a single commit with the generated message
6. Push: `git push`

If in .impl/ folder:

1. DO NOT delete .impl/
2. DO NOT auto-commit
3. Leave changes for user review
```

### Step 2: Update Step 10 for PR creation

The PR creation step should use the newly created commit message. Update to reference the commit message from the single implementation commit.

## Testing

After the fix:
1. Run `/erk:plan-implement` in a worktree with `.worker-impl/`
2. Verify the commit message does NOT reference `.worker-impl/` files
3. Verify the PR body does NOT reference `.worker-impl/` files
4. Verify only one implementation commit is created (not separate cleanup commit)

## Critical Files

- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-implement.md`