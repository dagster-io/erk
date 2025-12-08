# Documentation Extraction Plan

## Objective

Add documentation for patterns discovered during erk stack list implementation, including a critical gotcha about WorktreeInfo.is_root detection.

## Source Information

- **Session ID**: ed888f5a-8ae0-4837-8eac-df3fec2c992c
- **Branch**: 2722-erk-stack-list-command-erk-12-08-0733
- **Context**: Implementation of `erk stack list` command with bug fix for root worktree detection

## Documentation Items

### 1. WorktreeInfo.is_root Pattern (Category A - Learning Gap)

**Location**: `docs/agent/architecture/` or tripwire
**Action**: Add new tripwire or pattern documentation
**Priority**: High - This bug cost debugging time

**Content**:

The `WorktreeInfo` dataclass has an `is_root` boolean field to indicate the root worktree. When determining if a worktree is root:

**CORRECT**: Use `wt.is_root`
```python
wt_name = "root" if wt.is_root else wt.path.name
```

**INCORRECT**: Compare paths
```python
# BUG: This fails when running from a worktree where repo.root may equal cwd
wt_name = wt.path.name if wt.path != repo.root else "root"
```

**Why path comparison fails**: When running from inside a non-root worktree, `discover_repo_context()` may return a `repo.root` that equals the current worktree path, causing all worktrees to incorrectly show as "root".

---

### 2. Test Scenario: Non-root Worktree Execution (Category A - Learning Gap)

**Location**: `docs/agent/testing/` or fake-driven-testing skill
**Action**: Add testing pattern guidance
**Priority**: Medium - Helps catch similar bugs

**Content**:

When testing worktree-related code, include tests that simulate running from a non-root worktree:

```python
def test_worktree_name_uses_is_root_flag() -> None:
    """Test from non-root worktree to catch path comparison bugs."""
    worktree_path = repo_dir / "worktrees" / "my-feature"
    
    git = FakeGit(
        worktrees={
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                WorktreeInfo(path=worktree_path, branch="my-feature", is_root=False),
            ],
        },
        # Key: set cwd to the NON-ROOT worktree
        current_branches={worktree_path: "my-feature"},
    )
    
    # Run from the non-root worktree
    test_ctx = env.build_context(git=git, cwd=worktree_path)
```

---

### 3. /debug-ci Command (Category B - Teaching Gap)

**Location**: Command index or reference documentation
**Action**: Document new command
**Priority**: Low - Command is self-documenting

**Content**:

`/debug-ci` - Fetches and analyzes failing CI logs for the current branch's PR. Uses `gh` CLI to:
1. Check PR status for failures
2. Find failed workflow run IDs
3. Fetch failed logs with `gh run view --log-failed`
4. Present common fixes (docs-sync, lint, format, etc.)

---

### 4. erk stack list Command (Category B - Teaching Gap)

**Location**: `docs/agent/glossary.md` under stack-related entries
**Action**: Add glossary entry
**Priority**: Low - CLI help is sufficient

**Content**:

**erk stack list** (alias: `erk stack ls`) - Lists the Graphite stack for the current branch, showing which branches have associated worktrees. Filters to branches with worktrees and displays a Rich table with branch name, worktree directory, and current branch marker.