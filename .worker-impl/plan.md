# Extraction Plan: Git Worktree Directory Resolution

## Objective

Document the git worktree directory resolution pattern for erk development.

## Source Sessions

- `78d582f1-bcfe-41a9-87d6-70cf9b5dcb34` - Bug fix session for worktree prune failure

---

## Documentation Items

### 1. Git Worktree Directory Resolution

**Type:** Category A (Learning Gap)
**Location:** `docs/agent/glossary.md` - Add entry
**Priority:** Medium
**Action:** Add glossary entry

**Draft Content:**

```markdown
## Git Common Dir vs Repo Root

**Problem:** When running from a git worktree, `repo_root` (or `git rev-parse --show-toplevel`) returns the worktree directory path, NOT the main repository where `.git/` lives.

**Solution:** Use `git rev-parse --git-common-dir` to find the actual git directory:

```bash
# Returns path to .git directory (shared across all worktrees)
git rev-parse --git-common-dir
```

**Key distinction:**
- `--show-toplevel`: Returns worktree root (the directory you're in)
- `--git-common-dir`: Returns the shared .git directory location

**When this matters:**
- Running git commands AFTER deleting a worktree (cwd no longer exists)
- Operations that need the main repository, not the worktree
- Subprocess execution where cwd must exist

**Example bug:**
```python
# BUG: If repo_root is the worktree being deleted, this fails
git.remove_worktree(repo_root, worktree_path, force=True)
git.prune_worktrees(repo_root)  # FAILS - repo_root no longer exists!

# FIX: Resolve main git dir BEFORE deletion
main_git_dir = find_main_git_dir(repo_root)  # Uses --git-common-dir
git.remove_worktree(repo_root, worktree_path, force=True)
git.prune_worktrees(main_git_dir)  # WORKS - main repo still exists
```
```

---

## Implementation Notes

- This is a glossary addition for quick reference
- Links to the `_find_main_git_dir()` helper being added in issue #2345