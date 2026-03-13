---
description: Resolve merge conflicts and continue rebase (headless)
---

# Resolve Merge Conflicts

Fix all merge conflicts in this repository and continue the rebase.

## Steps

1. **Identify conflicts** - Run `git status` to identify all conflicted files.

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
   - If genuinely unclear, prefer the incoming (upstream) version

   d. **Remove all conflict markers** (`<<<<<<<`, `=======`, `>>>>>>>`).

   e. **Stage the resolution**: `git add <file>`

4. **Continue the rebase** - After resolving all conflicts, stage resolved files and run `git rebase --continue`.

5. **Repeat** - If more conflicts appear, repeat from step 1.

6. **Regenerate auto-generated files** - After rebase completes, regenerate any auto-generated files resolved in step 2 (e.g., run `erk docs sync`).
