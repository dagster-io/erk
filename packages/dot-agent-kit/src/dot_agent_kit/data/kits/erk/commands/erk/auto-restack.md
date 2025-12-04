---
description: Automate Graphite restacking with intelligent conflict resolution
---

# Auto Restack

🔄 Automated Graphite restack with intelligent merge conflict resolution.

This command runs `gt restack` and automatically handles any merge conflicts that arise, looping until the restack completes successfully.

## What This Command Does

1. **Squashes commits** - Consolidates all commits into one before restacking
2. **Runs `gt restack`** - Starts the restack operation
3. **Checks for conflicts** - Monitors `git status` for conflicted files
4. **Resolves conflicts intelligently** - Distinguishes between:
   - **Semantic conflicts**: Alerts user for manual decision
   - **Mechanical conflicts**: Auto-resolves when safe
5. **Continues restacking** - Stages files and runs `gt continue`
6. **Loops until complete** - Repeats until no more conflicts
7. **Verifies success** - Confirms clean git status

## Implementation

### Step 0: Squash Commits First

Before restacking, squash all commits into one to simplify conflict resolution:

```bash
dot-agent run gt idempotent-squash --format json
```

Parse the JSON result:

- If `success: true` with `action: "squashed"` or `action: "already_single_commit"`: Continue to Step 1
- If `success: false` with `error: "squash_conflict"`: Report the squash conflict and stop
- If `success: false` with `error: "no_commits"`: Report no commits ahead of trunk and stop
- If `success: false` with other error: Report the error and stop

This ensures only a single commit needs to be rebased, minimizing potential conflicts.

### Step 1: Start the Restack

```bash
gt restack --no-interactive
```

If the command succeeds without conflicts, skip to Step 5.

### Step 2: Check for Conflicts

Run `git status` to identify the state:

- If no conflicts (clean or rebase complete): Go to Step 5
- If conflicts exist: Continue to Step 3

### Step 3: Resolve Conflicts

For each conflicted file identified by `git status`:

<!-- prettier-ignore -->
@../../docs/erk/includes/conflict-resolution.md

### Step 4: Continue the Restack

After resolving all conflicts:

1. If project memory includes a precommit check, run it and ensure no failures
2. Stage the resolved files:

```bash
git add <resolved-files>
```

3. Continue the restack:

```bash
gt continue
```

4. **Loop back to Step 2** - Check if more conflicts arise

### Step 5: Verify Completion

Check `git status` to confirm:

- No ongoing rebase
- Clean working directory
- Successful restack completion

Display success message with summary of what was resolved.

**IMPORTANT: Do not suggest specific next actions** (like "push" or "submit PR"). The user knows what they were doing before the restack was needed. Just confirm the branch is ready.

## Error Handling

### Pre-commit Hook Failures

If pre-commit hooks fail after conflict resolution:

1. Fix the issues raised by the hooks
2. Re-stage the files
3. Continue with `gt continue`

### Unresolvable Conflicts

If a conflict cannot be safely auto-resolved (semantic conflict), the command will pause and ask for user input before proceeding.

### Restack Already in Progress

If a restack is already in progress when the command starts, it will detect this from `git status` and continue from the conflict resolution phase.

## Example Output

```
🔄 Starting Graphite restack...

⚡ Conflict detected in 2 files:
   - src/utils.py (mechanical - auto-resolving)
   - src/config.py (mechanical - auto-resolving)

✅ Resolved 2 mechanical conflicts
📦 Staged resolved files
▶️  Continuing restack...

⚡ Conflict detected in 1 file:
   - src/api.py (semantic - requires decision)

🤔 Semantic conflict in src/api.py:
   HEAD: Implements retry logic with exponential backoff
   INCOMING: Implements retry logic with fixed delay

   Which approach should be used?
   1. Keep HEAD (exponential backoff)
   2. Keep INCOMING (fixed delay)
   3. Combine both approaches

[User chooses option 1]

✅ Resolved conflict with user's choice
📦 Staged resolved files
▶️  Continuing restack...

✅ Restack complete! Your branch is ready.
```
