# Work Without Plans

Quick changes without formal plans. Use this workflow for simple fixes, small features, and rapid iteration when upfront planning would slow you down more than help.

## When to Skip Planning

Skip planning for:

- **Bug fixes** - Straightforward fixes with obvious solution
- **Documentation updates** - README changes, typo fixes, doc improvements
- **Refactoring** - Renaming, code organization, style improvements
- **Small features** - Single-file changes, simple additions
- **Experiments** - Trying something to see if it works
- **Revisions** - Addressing PR feedback, fixing failing CI

**Rule of thumb:** If you can describe the entire change in 1-2 sentences, skip planning.

## Creating a Worktree

Create an isolated worktree for your changes:

```bash
erk wt create my-feature-name
```

This creates a new worktree in `../<timestamp>-my-feature-name/` and:

- Creates a new branch
- Checks out the branch in the worktree
- Sets up git configuration
- Opens the worktree in your shell

**Tip:** Use descriptive branch names. `fix-auth-bug` is better than `fix`.

## Making Changes

Work normally in Claude Code:

1. **Describe the change** - "Fix the authentication timeout bug"
2. **Let Claude iterate** - Claude uses Read, Edit, Write tools
3. **Verify locally** - Test your changes work
4. **Commit as you go** - Use `/erk:git-pr-push` for atomic commits

**No .impl/ folder** - Planless workflow doesn't use `.impl/` or progress tracking.

## Submitting the PR

Once your changes are ready:

```bash
erk pr submit
```

This:

- Stages all changes
- Generates AI commit message from diff
- Creates commit with proper attribution
- Pushes branch to remote
- Creates PR via `gh pr create --fill`

**PR state:** Opens as ready for review (not draft).

## Landing

After PR approval:

```bash
erk pr land
```

Or use the `/erk:land` slash command in Claude Code.

This:

- Fetches latest from remote
- Rebases PR branch on trunk
- Handles any conflicts (with Claude's help if using slash command)
- Merges to trunk
- Pushes to remote
- Cleans up worktree and branch

**Objective integration:** If the PR is associated with an objective, `/erk:land` automatically updates the objective issue after landing.

## Quick Submit

For rapid iteration during development:

```bash
/local:quick-submit
```

This streamlined command:

- Commits all changes with AI-generated message
- Submits via Graphite (`gt submit`)
- Skips confirmation prompts

**Use when:** Making frequent small updates during active development.

**Don't use:** For final PR submission or when you need careful review of what's being committed.

## Troubleshooting

### Merge Conflicts

If rebasing fails during landing:

1. **Use `/erk:fix-conflicts`** - Claude helps resolve conflicts
2. **Or manually resolve** - Edit conflicting files, then `git rebase --continue`
3. **Re-run landing** - Continue the `erk pr land` process

### Failed CI Checks

When CI fails on your PR:

1. **Use `/local:debug-ci`** - Analyzes failures and suggests fixes
2. **Fix locally** - Make corrections in your worktree
3. **Submit again** - Use `erk pr submit` to update the PR

### Stacked Changes

If you need to make changes that depend on uncommitted work:

1. **Commit current work** - Use `/erk:git-pr-push`
2. **Create stacked worktree** - `erk wt create next-feature` (creates branch off current)
3. **Make new changes** - Work in the stacked worktree
4. **Submit independently** - Each worktree tracks its own PR

## When to Switch to Planning

Switch to planning workflow if you find yourself:

- **Working for >2 hours** - The change is bigger than expected
- **Touching 5+ files** - Scope is expanding
- **Uncertain about approach** - Multiple valid solutions exist
- **Needing research** - Have to understand existing code first
- **Making architectural changes** - Affects multiple components

**How to switch:**

1. **Stop coding** - Don't continue down uncertain path
2. **Enter plan mode** - Let Claude create a plan with research
3. **Save plan** - Use `/erk:plan-save`
4. **Implement from plan** - Use `/erk:plan-implement`

See [When to Switch to Planning Pattern](../learned/documentation/when-to-switch-pattern.md) for detailed decision framework.

## Collaboration

### Working with Others

**Before starting work:**

```bash
# Check if someone else is working on similar changes
gh pr list --search "label:in-progress"
```

**During development:**

- Mark PR as draft if not ready for review
- Use descriptive commit messages
- Keep PR scope focused

**After submission:**

- Respond to review feedback promptly
- Use `erk pr submit` to update PR with fixes
- Don't force-push - rebasing is handled by `erk pr land`

### Learn Workflow Integration

After landing a PR without a plan:

```bash
erk learn --from-pr <pr-number>
```

This extracts learnings from the implementation session for future documentation.

**When to use:** After implementing something novel or discovering patterns worth documenting.

## See Also

- [Use the Local Workflow](local-workflow.md) - Full planning workflow
- [Worktrees](../topics/worktrees.md) - Understanding worktrees
- [When to Switch to Planning](../learned/documentation/when-to-switch-pattern.md) - Decision framework
- [Quick Submit Command](../learned/commands/) - Rapid iteration command details
