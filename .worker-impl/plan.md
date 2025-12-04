## Extraction Plan

**Session:** 25a909c4-5963-42f0-ad33-bee7168fc872
**Created:** 2025-12-04

## Context

During implementation of worktree tracking (PR #2098), significant debugging was required to understand how FakeGit handles path resolution, worktree lookups, and macOS symlink differences. The fixes revealed patterns that should be documented to prevent similar debugging time in future sessions.

---

## Suggested Improvements

### 1. Update FakeGit Reference in Testing Docs (Category B - Teaching)

**Target:** `docs/agent/testing/testing.md`

**What to add:** Enhanced FakeGit documentation covering path resolution patterns.

**Draft content:**

```markdown
### FakeGit Path Resolution

FakeGit methods that accept paths perform intelligent lookups:

**`get_git_common_dir(cwd)`** - Walks up parent directories to find a match, handles symlink resolution (macOS `/var` vs `/private/var`).

**`get_repository_root(cwd)`** - Resolution order:
1. Explicit `repository_roots` mapping
2. Inferred from `worktrees` (finds deepest worktree containing cwd)
3. Derived from `git_common_dirs` (parent of .git directory)
4. Falls back to cwd

**`list_worktrees(repo_root)`** - Can be called from any worktree path or main repo, not just the dict key.

**Common Gotcha:** When testing subdirectories of worktrees, you often don't need to configure `repository_roots` explicitly - FakeGit infers it from the `worktrees` configuration.

```python
# Testing from a subdirectory of a worktree
git_ops = FakeGit(
    worktrees={
        main_repo: [
            WorktreeInfo(path=main_repo, branch="main", is_root=True),
            WorktreeInfo(path=worktree_path, branch="feature", is_root=False),
        ]
    },
    git_common_dirs={subdirectory: main_repo / ".git"},
    # No need for repository_roots - inferred from worktrees
)
```
```

---

### 2. Add RepoContext Semantics to Glossary (Category B - Teaching)

**Target:** `docs/agent/glossary.md`

**What to add:** Entry explaining the distinction between `root` and `main_repo_root`.

**Draft content:**

```markdown
### RepoContext.root vs RepoContext.main_repo_root

- **`root`**: The working tree root where git commands should run. For worktrees, this is the worktree directory. For main repos, equals `main_repo_root`.

- **`main_repo_root`**: The main repository root (consistent across all worktrees). Used for:
  - Deriving `repo_name` for metadata paths
  - Operations that need the root worktree (e.g., escaping from a worktree being deleted)
  - Resolving "root" as a target in commands like `stack move root`

**Key insight:** When running from a worktree, git commands use `root` (the worktree), but metadata and escaping use `main_repo_root` (the main repo).
```

---

### 3. Document macOS Symlink Pattern (Category A - Learning)

**Target:** `docs/agent/testing/testing.md` or new section

**What to add:** Pattern for handling `/var` vs `/private/var` on macOS.

**Draft content:**

```markdown
### macOS Symlink Resolution

On macOS, `/tmp` and `/var` are symlinks to `/private/tmp` and `/private/var`. When paths are resolved:
- `Path("/tmp/foo").resolve()` → `/private/tmp/foo`
- `Path("/var/folders/...").resolve()` → `/private/var/folders/...`

**Impact on tests:** If FakeGit is configured with unresolved paths but the code under test calls `.resolve()`, lookups fail.

**FakeGit handles this automatically** - all path lookups resolve both the input and configured paths before comparison. You generally don't need to worry about this.

**If you see path mismatch errors:** Ensure FakeGit's path resolution methods are being used (they handle symlinks), not direct dict lookups.
```

---

## Implementation Notes

- Improvements 1 and 3 should be added to `docs/agent/testing/testing.md`
- Improvement 2 should be added to `docs/agent/glossary.md`
- All are teaching gaps (documenting what was built), not learning gaps