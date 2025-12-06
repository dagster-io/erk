---
title: Auto-Restack Command Usage
read_when:
  - "using erk pr auto-restack"
  - "dealing with rebase conflicts in Graphite stacks"
  - "automating conflict resolution"
  - "understanding when to use auto-restack vs manual gt restack"
---

# Auto-Restack Command Usage

The `erk pr auto-restack` command automates Graphite restacking with intelligent conflict resolution. It runs `gt restack` and automatically handles merge conflicts, looping until completion.

## When to Use Auto-Restack

**Use auto-restack when:**

- Your Graphite stack is out of date with trunk
- You need to update branch dependencies
- You expect mechanical conflicts (import changes, formatting, etc.)
- You want hands-off conflict resolution

**Use manual `gt restack` when:**

- You need precise control over each conflict
- Conflicts involve complex semantic decisions
- You're debugging restack issues
- You prefer interactive resolution

## Basic Usage

```bash
# Run from any branch in your stack
erk pr auto-restack
```

The command will:

1. Squash commits on your branch
2. Attempt `gt restack --no-interactive`
3. Resolve conflicts automatically when possible
4. Ask for input on semantic conflicts
5. Continue until restack completes

## What Happens During Execution

### Phase 1: Preflight

```
🔄 Starting Graphite restack...
📦 Squashing commits...
🔄 Running gt restack...
```

The preflight:

- Squashes all commits on the current branch into one
- Runs `gt restack --no-interactive`
- Detects any conflicts that arise

If no conflicts, the restack completes immediately.

### Phase 2: Conflict Resolution Loop

When conflicts are detected:

```
⚡ Conflict detected in 2 files:
   - src/utils.py (mechanical - auto-resolving)
   - src/config.py (mechanical - auto-resolving)

✅ Resolved 2 mechanical conflicts
📦 Staging resolved files and continuing...
```

The command classifies each conflict:

**Mechanical conflicts** (auto-resolved):

- Adjacent line changes
- Import reordering
- Formatting differences
- Independent features touching the same file

**Semantic conflicts** (requires user input):

- Different approaches to the same problem
- Architectural disagreements
- Contradictory business logic

For semantic conflicts, you'll be prompted:

```
🤔 Semantic conflict in src/api.py:
   HEAD: Implements retry logic with exponential backoff
   INCOMING: Implements retry logic with fixed delay

   Which approach should be used?
   1. Keep HEAD (exponential backoff)
   2. Keep INCOMING (fixed delay)
   3. Combine both approaches
```

### Phase 3: Finalize

```
✅ Restack complete! Your branch is ready.
```

The finalize verifies:

- No rebase is still in progress
- Working tree is clean

## Example: Successful Run

```
$ erk pr auto-restack
🔄 Starting Graphite restack...
📦 Squashing commits...
✅ Commits squashed (3 → 1)
🔄 Running gt restack...
✅ Restack completed successfully

✅ Restack complete!
```

## Example: Run with Conflicts

```
$ erk pr auto-restack
🔄 Starting Graphite restack...
📦 Squashing commits...
✅ Commits squashed (2 → 1)
🔄 Running gt restack...

⚡ Conflict detected in 3 files:
   - packages/erk-shared/src/erk_shared/git/fake.py
   - packages/erk-shared/src/erk_shared/graphite/fake.py
   - src/erk/cli/commands/pr/submit_cmd.py

Analyzing conflicts...
   - fake.py (mechanical): Tuple type annotation merge
   - fake.py (mechanical): Constructor parameter updates
   - submit_cmd.py (mechanical): Import reordering

✅ Resolved 3 mechanical conflicts
📦 Staging resolved files and continuing...

✅ Restack completed successfully

✅ Restack complete!
```

## Troubleshooting

### Preflight False Positives

**Issue:** Preflight reports conflicts but you expected none.

**Cause:** Your branch may have diverged more than expected from trunk.

**Solution:**

1. Check `git log --oneline main..HEAD` to see your commits
2. Check `git log --oneline HEAD..main` to see trunk commits
3. Consider rebasing manually if the divergence is significant

### Semantic Conflicts Requiring User Input

**Issue:** Command stops and asks for decisions.

**Cause:** Conflicts involve conflicting intent that can't be auto-resolved.

**Solution:**

1. Read the conflict description carefully
2. Choose the appropriate approach based on your feature's needs
3. The command continues after your choice

### Rebase Already in Progress

**Issue:** Error about existing rebase in progress.

**Cause:** A previous rebase was interrupted.

**Solution:**

```bash
# Option 1: Continue the existing rebase
gt continue

# Option 2: Abort and start fresh
gt rebase --abort
erk pr auto-restack
```

### Pre-commit Hook Failures

**Issue:** Pre-commit hooks fail after conflict resolution.

**Cause:** Resolved code doesn't pass linting/formatting.

**Solution:** The auto-restack command will:

1. Show the pre-commit failure
2. Fix the issues (formatting, imports, etc.)
3. Continue automatically

If issues can't be auto-fixed, you'll need to fix them manually.

## Architecture

The auto-restack command uses a three-phase architecture:

1. **Preflight** - Squash + restack attempt + conflict detection
2. **Continue Loop** - Resolve, stage, continue until complete
3. **Finalize** - Verify clean completion

For implementation details, see [Three-Phase Restack Architecture](../architecture/restack-operations.md).

## Related Documentation

- [Three-Phase Restack Architecture](../architecture/restack-operations.md) - Technical implementation
- [Graphite Branch Setup](graphite-branch-setup.md) - Setting up branches before submission
- Load `gt-graphite` skill for comprehensive Graphite guidance
