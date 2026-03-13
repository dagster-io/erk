---
description: Resolve merge conflicts from an in-progress rebase
---

<!-- Canonical conflict resolution logic: .claude/commands/erk/system/resolve-conflicts-core.md -->

# Resolve Conflicts from In-Progress Rebase

Resolve merge conflicts from a rebase that is already in progress. This command does NOT initiate a rebase -- it only resolves conflicts from one that has already started.

## Steps

1. **Check status** - Run `git status` to understand the state of the rebase and identify conflicted files

2. **Separate auto-generated files from real content** - For each conflicted file, check for the `<!-- AUTO-GENERATED FILE -->` header comment:
   - **Auto-generated files** (e.g., `tripwires.md`, `index.md` with the auto-generated header): Accept either side with `git checkout --theirs <file>`, stage with `git add`. After the rebase completes, regenerate them (e.g., `erk docs sync` for tripwires/index files).
   - **Real content files**: Proceed to step 3.

3. **Resolve each real content file:**

   a. **Read the file** and understand both sides of the conflict:
   - `<<<<<<< HEAD` = local changes
   - `=======` separates local from incoming
   - `>>>>>>> <commit>` = incoming changes

   b. **Determine what each side was trying to accomplish.**

   c. **Resolve intelligently:**
   - If changes are complementary, merge both
   - If changes conflict semantically, prefer the more recent/complete version
   - If genuinely unclear, ask the user for guidance

   d. **Remove all conflict markers** (`<<<<<<<`, `=======`, `>>>>>>>`).

   e. **Stage the resolution**: `git add <file>`

4. **Continue the rebase** - After resolving all conflicts, stage resolved files and run `git rebase --continue`.

5. **Repeat** - If the rebase continues with more conflicts, repeat from step 1.

6. **Regenerate auto-generated files** - After rebase completes, regenerate any auto-generated files resolved in step 2:
   - For tripwires/index files: `erk docs sync`
   - Commit the regenerated files separately

7. **Verify completion** - Check git status and recent commit history to confirm success

8. **Ask user about pushing** - After rebase, the branch will have diverged from origin. Use `AskUserQuestion` to ask the user how they'd like to proceed, presenting these options:
   - **Push with Graphite**: `gt submit --no-interactive`
   - **Push with git**: `git push --force-with-lease`
   - **Do nothing**: skip pushing (user will handle manually)
