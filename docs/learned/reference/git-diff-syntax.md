---
title: Git Diff Dot Notation Syntax
read_when:
  - "writing git diff commands"
  - "comparing branches with git"
  - "understanding three-dot vs two-dot git syntax"
tripwires:
  - action: "using two-dot syntax (branch..HEAD) in git diff"
    warning: "git diff comparisons MUST use three-dot (branch...HEAD) to diff from merge-base. Two-dot is correct for git rev-list but WRONG for git diff."
---

# Git Diff Dot Notation Syntax

Git's dot notation has different semantics for `git diff` vs `git rev-list`/`git log`. Using the wrong notation produces incorrect results.

## Two-Dot (`A..B`)

- **`git rev-list A..B`**: Commits reachable from B but not A (correct for counting)
- **`git diff A..B`**: Diff between A and B directly (NOT from merge-base). If A and B have diverged, this includes changes from both sides, producing spurious files.

## Three-Dot (`A...B`)

- **`git rev-list A...B`**: Commits reachable from either but not both (symmetric difference)
- **`git diff A...B`**: Diff from merge-base of A and B to B. Shows only changes introduced on B's side. **This matches GitHub's PR diff behavior.**

## Correct Pattern for PR-Style Diffs

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/real.py, get_diff_to_branch -->

```
git diff branch...HEAD    # Correct: diff from merge-base
git diff branch..HEAD     # WRONG: includes both sides of divergence
```

The `get_diff_to_branch()` function in `packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/real.py` (RealGitAnalysisOps class) uses three-dot syntax to match GitHub's PR diff behavior.

## Quick Reference

| Command        | Two-dot (`..`)                  | Three-dot (`...`)                 |
| -------------- | ------------------------------- | --------------------------------- |
| `git diff`     | Direct diff (wrong for PRs)     | From merge-base (correct for PRs) |
| `git rev-list` | Commits in B not in A (correct) | Symmetric difference              |
| `git log`      | Commits in B not in A (correct) | Commits in either, not both       |
