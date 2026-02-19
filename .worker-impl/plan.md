# Fix `command-organization.md` — incorrect `erk implement` descriptions

## Context

`docs/learned/cli/command-organization.md` incorrectly describes `erk implement` as creating worktrees. In reality:

- **`erk prepare`** — allocates a slot, creates a worktree, creates a branch from a plan issue, sets up `.impl/`
- **`erk implement`** — works in-place in the current directory, sets up `.impl/` from a plan issue, no worktree allocation

The doc says "Most worktrees are created automatically via `erk implement`" (line 72) and "Create worktree and start work" (line 295). This caused confusion during objective #7599 planning and will mislead future agents.

## Changes

**File: `docs/learned/cli/command-organization.md`**

1. **Line 51** — `implement` description in the table: change from "Start implementing a plan" to "Implement a plan in current directory"

2. **Lines 70-74** — Worktree "Why grouped?" section: replace the incorrect claim that `erk implement` creates worktrees. Correct to say worktrees are created via `erk prepare`:
   ```
   - Lower frequency: Worktrees are created via `erk prepare`, not during normal plan implementation
   ```

3. **Line 295** — Plan Lifecycle example: fix the comment from `# Create worktree and start work` to `# Set up .impl/ and implement in current directory`

4. **Lines 310-311** — Worktree Management example: fix the comment from `# Create worktrees (rare - usually via implement)` to `# Create worktrees (via prepare or directly)`

5. **Add `erk prepare` to the top-level plan commands listing** (lines 22-31) since it's a top-level command and part of the plan workflow:
   ```bash
   erk prepare       # Create worktree from a plan issue
   ```
   Also add it to the table at lines 45-53.

## Verification

- Read the updated doc to confirm accuracy against `src/erk/cli/commands/prepare.py` and `src/erk/cli/commands/implement.py`
- Grep for any other docs that make the same incorrect claim about `erk implement` creating worktrees