# Fix: Replace N `git rev-parse` calls with single `git for-each-ref` in Graphite branch cache

## Context

`RealGraphite.get_all_branches()` enriches every tracked Graphite branch with its commit SHA by calling `git rev-parse <branch>` individually — one subprocess per branch. With 30-50 tracked branches, this adds ~150-500ms to every `erk dash` load (on first call per session, before the mtime cache kicks in).

A single `git for-each-ref` call returns all branch heads at once in ~5ms.

## Approach

Add `get_all_branch_heads()` to the `BranchOps` gateway (5-place update), then use it in `RealGraphite.get_all_branches()` instead of the per-branch loop.

### Step 1: Add `get_all_branch_heads` to BranchOps ABC

**File**: `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/abc.py` (after `get_branch_head` at line 142)

```python
@abstractmethod
def get_all_branch_heads(self, repo_root: Path) -> dict[str, str]:
    """Get commit SHAs for all local branches in a single call.

    Args:
        repo_root: Path to the git repository root

    Returns:
        Mapping of branch name to commit SHA.
    """
    ...
```

### Step 2: Implement in `real.py`

**File**: `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py` (after `get_branch_head` at line 162)

Uses `git for-each-ref` — the same pattern already used by `get_all_branch_sync_info` at line 270 in the same file.

```python
def get_all_branch_heads(self, repo_root: Path) -> dict[str, str]:
    """Get commit SHAs for all local branches in a single call."""
    result = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)\t%(objectname:short)", "refs/heads/"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}
    heads: dict[str, str] = {}
    for line in result.stdout.strip().split("\n"):
        if "\t" in line:
            branch, sha = line.split("\t", 1)
            heads[branch] = sha
    return heads
```

### Step 3: Implement in `fake.py`

**File**: `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/fake.py` (after `get_branch_head` at line 285)

```python
def get_all_branch_heads(self, repo_root: Path) -> dict[str, str]:
    """Get commit SHAs for all local branches."""
    return dict(self._branch_heads)
```

### Step 4: Implement in `dry_run.py` and `printing.py`

Both delegate to `self._wrapped`:

**File**: `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/dry_run.py` (after `get_branch_head` at line 79)
**File**: `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/printing.py` (after `get_branch_head` at line 72)

```python
def get_all_branch_heads(self, repo_root: Path) -> dict[str, str]:
    """Get commit SHAs for all local branches."""
    return self._wrapped.get_all_branch_heads(repo_root)
```

### Step 5: Use in `RealGraphite.get_all_branches`

**File**: `packages/erk-shared/src/erk_shared/gateway/graphite/real.py` (lines 163-170)

Replace the per-branch loop:

```python
# Before (N subprocess calls):
git_branch_heads = {}
branches_data = data.get("branches", [])
for branch_name, _ in branches_data:
    if isinstance(branch_name, str):
        commit_sha = git_ops.branch.get_branch_head(repo_root, branch_name)
        if commit_sha:
            git_branch_heads[branch_name] = commit_sha

# After (1 subprocess call):
all_heads = git_ops.branch.get_all_branch_heads(repo_root)
branches_data = data.get("branches", [])
git_branch_heads = {}
for branch_name, _ in branches_data:
    if isinstance(branch_name, str) and branch_name in all_heads:
        git_branch_heads[branch_name] = all_heads[branch_name]
```

## Files to modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/abc.py` | Add `get_all_branch_heads` abstract method |
| `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py` | Implement via `git for-each-ref` |
| `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/fake.py` | Return from `_branch_heads` dict |
| `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/dry_run.py` | Delegate to `_wrapped` |
| `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/printing.py` | Delegate to `_wrapped` |
| `packages/erk-shared/src/erk_shared/gateway/graphite/real.py` | Use `get_all_branch_heads` instead of per-branch loop |

## Verification

1. Run tests: `pytest`
2. Type check: `ty check`
3. Lint: `ruff check && ruff format --check`
