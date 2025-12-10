---
description: Automate Graphite restacking with intelligent conflict resolution
---

# Auto Restack

🔄 Automated Graphite restack with intelligent merge conflict resolution.

This command runs `gt restack` and automatically handles any merge conflicts that arise, looping until the restack completes successfully.

## What This Command Does

1. **Preflight** - Squashes commits and attempts restack, detecting conflicts
2. **Conflict loop** - For each set of conflicts:
   - Resolves conflicts (semantic vs mechanical)
   - Stages resolved files and continues
3. **Finalize** - Verifies clean completion

## Implementation

### Step 1: Run Preflight

```bash
dot-agent run gt restack-preflight
```

Parse the JSON result:

- If `success: true` and `has_conflicts: false`: Restack completed, skip to Step 3
- If `success: true` and `has_conflicts: true`: Conflicts detected, continue to Step 2 with `conflicts` list
- If `success: false`: Report error and stop (includes `error_type`: "squash_conflict", "squash_failed", "no_commits", etc.)

### Step 2: Resolve Conflicts Loop

While there are conflicts:

#### 2a: Resolve Each Conflict

**CRITICAL: You MUST resolve ALL files in the `conflicts` list before continuing.** Missing even one file will cause the restack to fail. Do not proceed to step 2b until every file has been resolved.

For each file in the `conflicts` list:

<!-- prettier-ignore -->
@../../docs/erk/includes/conflict-resolution.md

#### 2b: Continue Restack

After resolving all current conflicts:

1. If project memory includes a precommit check, run it and ensure no failures
2. Continue the restack (stages files and runs gt continue):

```bash
dot-agent run gt restack-continue <resolved-files...>
```

Parse the JSON result:

- If `restack_complete: true`: Done with conflicts, go to Step 3
- If `has_conflicts: true`: More conflicts found, loop back to 2a with new `conflicts` list
- If `success: false`: Report error and stop

### Step 3: Verify Completion

```bash
dot-agent run gt restack-finalize
```

Parse the JSON result:

- If `success: true`: Display success message
- If `success: false` with `error_type: "unresolved_conflicts"`: **Loop back to Step 2** - there are files you missed resolving. The error includes the list of unresolved files.
- If `success: false` with other error types: Report the issue (rebase still in progress, dirty working tree)

**IMPORTANT: Do not suggest specific next actions** (like "push" or "submit PR"). The user knows what they were doing before the restack was needed. Just confirm the branch is ready.

## Error Handling

### Pre-commit Hook Failures

If pre-commit hooks fail after conflict resolution:

1. Fix the issues raised by the hooks
2. Run `restack-continue` again with the fixed files

### Unresolvable Conflicts

If a conflict cannot be safely auto-resolved (semantic conflict), ask for user input before proceeding.

### Restack Already in Progress

If a restack is already in progress when the command starts, the preflight will detect this and report conflicts immediately.

## Example Output

```
🔄 Starting Graphite restack...

⚡ Conflict detected in 2 files:
   - src/utils.py (mechanical - auto-resolving)
   - src/config.py (mechanical - auto-resolving)

✅ Resolved 2 mechanical conflicts
📦 Staging resolved files and continuing...

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
📦 Staging resolved files and continuing...

✅ Restack complete! Your branch is ready.
```
