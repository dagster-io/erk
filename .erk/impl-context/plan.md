# Fix: Move impl-context cleanup to run after all setup paths

## Context

`.erk/impl-context/` is a git-tracked staging directory created during plan-save for draft-PR plans. It must be removed before implementation begins, or it leaks into the final PR. Currently, the cleanup lives inside Step 2d (line 175), which is only reachable via Path 1c (fresh plan save). Three other paths skip directly to Step 3, bypassing cleanup entirely.

## File Modified

`.claude/commands/erk/plan-implement.md`

## Changes

### 1. Remove Step 2d from current location (lines 175-187)

Delete the entire `### Step 2d: Clean Up Plan Staging Directory` section and its content.

### 2. Insert new Step 2d as a convergence point before Step 3 (after line 187, before line 189)

Insert a new section with updated heading and description making clear this runs for ALL paths:

````markdown
### Step 2d: Clean Up Plan Staging Directory (All Paths)

**All setup paths converge here before Step 3.** If `.erk/impl-context/` exists in git tracking (from draft-PR plan save), remove it:

\```bash
if [ -d .erk/impl-context/ ]; then
git rm -rf .erk/impl-context/
git commit -m "Remove .erk/impl-context/ before implementation"
git push origin "$(git branch --show-current)"
fi
\```

This directory contains plan content committed during plan-save. It is idempotent — safe to run even when the directory doesn't exist.
````

### 3. Update three "Skip to Step 3" references to "Skip to Step 2d"

- **Line 63** (Step 1a, `has_issue_tracking: false`): Change `**Skip directly to Step 3**` to `**Skip directly to Step 2d**`
- **Line 124** (Step 1b, `has_issue_tracking: false`): Change `**Skip directly to Step 3**` to `**Skip directly to Step 2d**`
- **Line 125** (Step 1b, `has_issue_tracking: true`): Change `proceed to Step 3` to `proceed to Step 2d`

### 4. Update Step 12 note (line 287)

The note already references Step 2d correctly. No change needed — the step number stays the same, it just moved.

## Path Trace Verification

After the change, all 5 paths pass through Step 2d:

| Path                    | Route                                             | Hits Cleanup?       |
| ----------------------- | ------------------------------------------------- | ------------------- |
| 1a (valid, no tracking) | 1a → **Step 2d** → Step 3                         | Yes                 |
| 1a (valid, tracking)    | 1a → setup-impl-from-issue → **Step 2d** → Step 3 | Yes (falls through) |
| 1a-file                 | 1a-file → impl-init → **Step 2d** → Step 3        | Yes (falls through) |
| 1b (valid)              | 1b → **Step 2d** → Step 3                         | Yes                 |
| 1c (plan save)          | Step 2 → 2b → 2c → **Step 2d** → Step 3           | Yes                 |

## Verification

- Read the modified file and trace all 5 paths to confirm each passes through cleanup
- No tests to run (command file, not code)
