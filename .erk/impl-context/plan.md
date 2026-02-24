# Document land cleanup force-delete and checked-out branch constraint

## Context

This plan captures documentation requirements from PR #8050, which addresses edge cases in erk's branch lifecycle management. The PR fixes a subtle git constraint: when creating a new branch from a remote ref (e.g., `origin/master`), if the user is currently on the local parent branch and that branch is behind remote, git refuses to force-update the checked-out branch. The fix adds a defensive check in GraphiteBranchManager that detects this situation upfront and skips the force-update, relying on `retrack_branch()` to handle any Graphite tracking divergence.

This change complements the work from PR #8049, which added force-delete to branch cleanup during `erk land`. Together, these PRs address the entry and exit sides of branch lifecycle: #8049 ensures branches can always be deleted during cleanup (diverged/unmerged branches), while #8050 ensures branches can be created safely when the parent is checked out.

The documentation updates are important because the checked-out branch constraint is a non-obvious git behavior that could confuse future developers working on branch operations. The defensive pattern (LBYL check before force-update) follows erk's coding standards but the underlying git constraint warrants explicit documentation.

## Raw Materials

No gist URL provided.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 2     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 0     |

## Documentation Items

### HIGH Priority

#### 1. GraphiteBranchManager checked-out branch constraint

**Location:** `docs/learned/architecture/git-graphite-quirks.md`
**Action:** UPDATE
**Source:** [PR #8050]

**Draft Content:**

```markdown
## Force-Update Limitation on Checked-Out Branches

**Surprising Behavior**: When creating a branch from a remote ref (e.g., `origin/master`) while the local parent branch is currently checked out and behind remote, git refuses to force-update the checked-out branch with an error.

**Why It's Surprising**: The branch creation flow in `GraphiteBranchManager.create_branch()` attempts to ensure the local parent matches remote before Graphite tracking. The code previously assumed the caller was never on the local parent branch, but this assumption was false. Users creating branches while on `master` would hit a git error.

**Solution**: `GraphiteBranchManager._ensure_local_matches_remote()` now checks if the local parent is currently checked out before attempting force-update:

1. Get the current branch using `git.branch.get_current_branch()`
2. If local_branch equals current_branch, skip force-update and return early
3. The `retrack_branch()` call handles any Graphite tracking divergence without requiring a force-update

**When This Happens**:

- User is on `master` branch
- They create a new branch from `origin/master`
- Local `master` is behind `origin/master`

**LBYL Pattern**: This follows erk's coding standard of checking conditions upfront rather than catching exceptions. The defensive check prevents the git error rather than handling it after the fact.

**Location in Codebase**: `packages/erk-shared/src/erk_shared/gateway/branch_manager/graphite.py` - `_ensure_local_matches_remote()` method
```

---

### MEDIUM Priority

#### 1. Land cleanup force-delete pattern

**Location:** `docs/learned/erk/branch-cleanup.md`
**Action:** UPDATE
**Source:** [PR #8049]

**Draft Content:**

```markdown
## Automated Cleanup During `erk land`

The `erk land` command automatically cleans up branches after successfully landing a PR. This cleanup uses force-delete (`git branch -D` / `force=True`) for all branch deletions.

### Why Force-Delete Is Required

During automated cleanup, branches may be in states that prevent normal deletion:

- **Diverged from remote**: Branch has local commits that differ from merged PR
- **Unmerged commits**: Git's `-d` flag refuses to delete branches with unmerged work
- **Rebased state**: After restacking, commit SHAs differ from what git considers "merged"

Force-delete bypasses these checks because the PR has already been merged to trunk -- the branch's purpose is complete regardless of its local state.

### Implementation Location

The cleanup functions in `src/erk/cli/commands/land_cmd.py` all pass `force=True` to `delete_branch()` calls. This includes cleanup after:

- Standard PR landing
- Stacked PR landing (multiple branches)
- Worktree-based landing

### Relationship to Manual Cleanup

This automated cleanup differs from the manual cleanup guide above. Manual cleanup (`git branch -d`) should still use safe deletion to catch unintentionally unmerged work. Automated cleanup (`erk land`) uses force-delete because the merge status is verified by the GitHub API before cleanup begins.
```

---

## Contradiction Resolutions

None found. The new insights are compatible with existing documentation.

## Stale Documentation Cleanup

None found. No phantom references detected in reviewed documentation files.

## Prevention Insights

### 1. Git force-update on checked-out branch failure

**What happened:** When creating a branch from a remote ref while on the local parent branch, the code attempted to force-update the checked-out branch, causing a git error.

**Root cause:** The assumption that callers would never be on the local parent branch when creating child branches was incorrect. Users commonly run `erk` commands while on `master` or other trunk branches.

**Prevention:** Add defensive LBYL check for current branch before attempting force-update operations. Check `git.branch.get_current_branch()` and compare against target branch.

**Recommendation:** TRIPWIRE

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Force-update on checked-out branch constraint

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, External tool quirk +1, Silent failure +1)

**Trigger:** Before force-updating a branch with git, check if it's currently checked out

**Warning:** Check if the branch is currently checked out. Git refuses force-updates on checked-out branches. Use `get_current_branch()` to detect and skip force-update, relying on retrack_branch() for Graphite tracking divergence.

**Target doc:** `docs/learned/architecture/git-graphite-quirks.md`

This is tripwire-worthy because:

1. **Non-obvious (+2)**: Git's rejection of force-updates on checked-out branches is not immediately clear from the code. Without this knowledge, developers might attempt force-updates that will fail unexpectedly.

2. **Cross-cutting (+2)**: This constraint applies anywhere in the codebase that attempts to force-update branches. The GraphiteBranchManager implementation handles this defensively, but the pattern could apply to other branch operations.

3. **External tool quirk (+1)**: This is a git-specific constraint, not an erk design decision. Understanding git's behavior is essential to implementing branch operations correctly.

4. **Silent failure (+1)**: Without documentation, future developers might not understand why the defensive check exists, potentially removing it as "unnecessary" code.

The harm without this tripwire: developers adding new branch manipulation code might attempt force-updates without the defensive check, causing user-facing errors when users happen to be on the target branch.

## Potential Tripwires

None identified. The only documentation item with tripwire potential (the checked-out branch constraint) meets the score threshold.
