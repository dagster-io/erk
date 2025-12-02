---
description: Automate Graphite restacking with intelligent conflict resolution
---

# Auto Restack

🔄 Automated Graphite restack with intelligent merge conflict resolution.

This command runs `gt restack` and automatically handles any merge conflicts that arise, looping until the restack completes successfully.

## What This Command Does

1. **Runs `gt restack`** - Starts the restack operation
2. **Checks for conflicts** - Monitors `git status` for conflicted files
3. **Resolves conflicts intelligently** - Distinguishes between:
   - **Semantic conflicts**: Alerts user for manual decision
   - **Mechanical conflicts**: Auto-resolves when safe
4. **Continues restacking** - Stages files and runs `gt continue`
5. **Loops until complete** - Repeats until no more conflicts
6. **Verifies success** - Confirms clean git status

## Implementation

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
@_conflict-resolution.md

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

✅ Restack complete! All branches are up to date.
```
