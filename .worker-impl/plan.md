# Plan: Complete howto/planless-workflow.md

**Part of Objective #4284, Step 2E.1**

## Goal

Complete the skeleton `docs/howto/planless-workflow.md` with actionable guidance for users who want to work without formal GitHub issue-based plans.

## Context

The planless workflow is an alternative to erk's default plan-oriented approach. Users should understand:
- When to skip formal planning
- How to create worktrees and branches directly
- How to submit PRs without plan linkage
- Commands for rapid iteration

## Implementation

### Single PR - Fill in Skeleton Sections

Transform the existing skeleton into complete documentation.

**File to modify:** `docs/howto/planless-workflow.md`

**Section content:**

1. **When to Skip Planning** - List scenarios where planless is appropriate:
   - Small bug fixes
   - Responding to PR review comments
   - Quick documentation updates
   - Iterating on existing work
   - Exploratory changes

2. **Creating a Worktree** - Document `erk wt create`:
   ```bash
   erk wt create --branch my-feature
   erk wt create --from-current-branch
   ```
   Note: No `--from-plan` flags = no `.impl/` folder

3. **Making Changes** - Standard Claude Code iteration:
   - Run `claude` in the worktree
   - Make changes interactively
   - No plan mode required for simple changes

4. **Submitting the PR** - Two options:
   - `/erk:git-pr-push` - Pure git workflow (recommended)
   - `erk pr submit` - Full-featured with Graphite

5. **Landing** - Same as planned workflow:
   ```bash
   erk land
   ```
   Works identically, just no plan/objective linking

6. **Quick Submit** - Document `/local:quick-submit`:
   - Generic "update" commit message
   - For rapid iteration cycles
   - Not for final PRs

7. **When to Switch to Planning** - Signs the change grew too complex:
   - Multiple files across different areas
   - Needs multi-session coordination
   - Should be tracked as a GitHub issue

## Files

| File | Action |
|------|--------|
| `docs/howto/planless-workflow.md` | Edit - fill in all skeleton sections |

## Verification

1. Read the completed doc to verify all TODO sections are filled
2. Verify internal links work (`local-workflow.md`, `../topics/worktrees.md`)
3. Run markdown lint if available
4. Ensure tone matches other how-to docs (task-focused, actionable)