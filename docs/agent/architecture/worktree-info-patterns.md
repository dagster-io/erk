---
title: WorktreeInfo Patterns and Pitfalls
read_when:
  - "working with WorktreeInfo dataclass"
  - "determining if a worktree is the root worktree"
  - "displaying worktree names in CLI output"
tripwires:
  - action: "determining if a worktree is root"
    warning: "Use `wt.is_root` field, NEVER compare paths. Path comparison fails when running from non-root worktrees."
---

# WorktreeInfo Patterns and Pitfalls

## Overview

The `WorktreeInfo` dataclass represents git worktree metadata. A critical field is `is_root`, which indicates whether the worktree is the root (main) worktree created with `git init`.

## Critical Pattern: Detecting Root Worktree

### The Correct Pattern

**ALWAYS use the `is_root` field** to determine if a worktree is the root worktree:

```python
from erk.integrations.git.abc import WorktreeInfo

def get_worktree_display_name(wt: WorktreeInfo) -> str:
    """Get display name for a worktree."""
    # ✅ CORRECT: Use is_root field
    return "root" if wt.is_root else wt.path.name
```

### The Incorrect Pattern (BUG)

**NEVER compare paths** to detect the root worktree:

```python
def get_worktree_display_name(wt: WorktreeInfo, repo_root: Path) -> str:
    """Get display name for a worktree."""
    # ❌ WRONG: Path comparison is unreliable
    return "root" if wt.path == repo_root else wt.path.name
```

## Why Path Comparison Fails

When you run erk from inside a non-root worktree:

1. `discover_repo_context()` may return a `repo.root` that equals the **current worktree path**
2. This causes ALL worktrees to incorrectly match `repo.root`
3. Every worktree appears to be "root", breaking display logic

### Example Failure Scenario

```
Repository structure:
/home/user/project/          ← Root worktree (main branch)
/home/user/project/worktrees/
  └── feature-x/             ← Non-root worktree (feature-x branch)

# Running from /home/user/project/worktrees/feature-x/
repo = discover_repo_context(Path.cwd())
# repo.root might equal /home/user/project/worktrees/feature-x/

# BUG: This comparison will be True for ALL worktrees
for wt in worktrees:
    is_root = (wt.path == repo.root)  # ❌ Incorrect for all worktrees
```

## The Solution: Use `is_root` Field

The `WorktreeInfo.is_root` field is populated by git's worktree metadata and is **always correct**, regardless of:

- Which worktree you're currently running from
- How `repo.root` is computed
- What `ctx.cwd` is set to

```python
# ✅ CORRECT: Reliable in all scenarios
for wt in worktrees:
    display_name = "root" if wt.is_root else wt.path.name
    print(f"{display_name}: {wt.branch}")
```

## Testing This Pattern

When writing tests for worktree-related code, **include tests that simulate running from a non-root worktree**:

```python
def test_worktree_name_uses_is_root_flag() -> None:
    """Test from non-root worktree to catch path comparison bugs."""
    repo_dir = Path("/repo")
    worktree_path = repo_dir / "worktrees" / "my-feature"

    git = FakeGit(
        worktrees={
            repo_dir: [
                WorktreeInfo(path=repo_dir, branch="main", is_root=True),
                WorktreeInfo(path=worktree_path, branch="my-feature", is_root=False),
            ],
        },
        # Key: set cwd to the NON-ROOT worktree
        current_branches={worktree_path: "my-feature"},
    )

    # Run from the non-root worktree
    test_ctx = env.build_context(git=git, cwd=worktree_path)

    # Verify root worktree is correctly identified
    result = list_worktrees(test_ctx)
    assert result[0].name == "root"  # First worktree
    assert result[1].name == "my-feature"  # Second worktree
```

See [Testing: Non-Root Worktree Execution](../testing/testing.md#non-root-worktree-testing) for more testing patterns.

## Related Patterns

- **Worktree Metadata**: See [Worktree Metadata Storage](worktree-metadata.md) for per-worktree data storage
- **Shell Integration**: See [Shell Integration Patterns](shell-integration-patterns.md) for worktree activation scripts
- **Fake Git**: See [Fake-Driven Testing](../testing/) for FakeGit constructor patterns

## Summary

| Pattern | Correct | Incorrect |
|---------|---------|-----------|
| **Root Detection** | `wt.is_root` | `wt.path == repo.root` |
| **Display Name** | `"root" if wt.is_root else wt.path.name` | `wt.path.name if wt.path != repo.root else "root"` |
| **Test Coverage** | Run from non-root worktree | Only test from repo root |

**Key Takeaway**: The `is_root` field is the source of truth. Path comparison is a bug waiting to happen.
