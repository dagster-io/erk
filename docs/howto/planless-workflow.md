# Work Without Plans

Quick changes without formal plans.

## When to Skip Planning

You don't need formal plans for:

- **Small bug fixes** - One-file changes with obvious solutions
- **Responding to PR review comments** - Addressing feedback on existing work
- **Quick documentation updates** - Typos, clarifications, or minor additions
- **Iterating on existing work** - Refining a feature you're already working on
- **Exploratory changes** - Trying something out to see if it works

The planless workflow is faster for changes that fit in your head and don't need multi-session coordination.

## Creating a Worktree

Create a worktree with a branch, but skip the `.impl/` folder:

```bash
# Create new branch from current location
erk wt create --branch my-feature

# Stack on top of current branch
erk wt create --from-current-branch
```

Without `--from-plan`, you get a clean worktree with no plan tracking.

## Making Changes

Work normally in the worktree:

1. Run `claude` to start Claude Code
2. Make changes interactively with the agent
3. Iterate until satisfied

For simple changes, you don't need to enter plan mode or create formal documentation.

## Submitting the PR

Choose the submission method that fits your workflow:

### Option 1: Git + GitHub CLI (Recommended)

Use `/erk:git-pr-push` for a pure git workflow:

```
/erk:git-pr-push "Add user authentication"
```

This creates a commit, pushes the branch, and opens a PR in one step.

### Option 2: Full-Featured with Graphite

Use `erk pr submit` for more control:

```bash
erk pr submit
```

This validates the PR, runs checks, and submits through Graphite's stack management.

## Landing

Landing works identically to planned workflows:

```bash
erk land
```

The only difference: no plan or objective issue gets updated.

## Quick Submit

For rapid iteration cycles, use `/local:quick-submit`:

```
/local:quick-submit
```

This creates a generic "update" commit and pushes immediately. Best for:

- Work-in-progress updates
- Quick fixes during review
- Pushing changes to trigger CI

**Not recommended** for final PRs - use descriptive commit messages instead.

## When to Switch to Planning

Consider creating a formal plan if:

- **Changes span multiple files** across different areas of the codebase
- **Work needs multi-session coordination** - You can't finish in one sitting
- **Changes should be tracked** as a GitHub issue for future reference
- **Implementation requires research** - You need to explore before coding
- **Scope keeps growing** - What started simple became complex

When in doubt: start planless, switch to planning if it grows.

## See Also

- [Use the Local Workflow](local-workflow.md) - Full planning workflow
- [Worktrees](../topics/worktrees.md) - Understanding worktrees
