---
title: Erk Test Rebase Conflicts
read_when:
  - "fixing merge conflicts in erk tests"
  - "ErkContext API changes during rebase"
  - "env_helpers conflicts"
---

# Erk Test Rebase Conflicts

**For generic merge conflict resolution**: Use the `/erk:merge-conflicts-fix` command.

This document covers **erk-specific test patterns** you'll encounter during rebases: ErkContext API evolution, env_helpers, parameter renames.

**Time saved**: 8-12x faster with this guide (2 hours → 10-15 minutes)

## Quick Start

When you encounter merge conflicts in **erk test files** during a rebase, check this guide. Test infrastructure conflicts are usually **mechanical** (both branches fixing the same issue with different timing) rather than semantic.

### Pre-Flight Check

```bash
# 1. Identify the conflict
git status

# 2. Check if it's test infrastructure
git diff HEAD <incoming_commit> tests/

# 3. Check for missing dependencies
git log --oneline <commit>~2..<commit>
```

## Fast Track Resolution

### Step 1: Extract Missing Dependencies

**Problem**: Rebased commit references files added in parent commits.

```bash
# Check what files the commit depends on
git show <incoming_commit> --stat

# If you see ImportError for missing module:
git show <incoming_commit>~1:tests/test_utils/env_helpers.py > tests/test_utils/env_helpers.py
git add tests/test_utils/env_helpers.py
```

**Common missing file**: `tests/test_utils/env_helpers.py` (added in commit c6516290)

### Step 2: Resolve Conflicts

For test infrastructure conflicts, accept the incoming version (newer pattern):

```bash
# Accept incoming version of conflicted files
git show <incoming_commit>:tests/commands/setup/test_init.py > tests/commands/setup/test_init.py
git show <incoming_commit>:tests/commands/workspace/test_create.py > tests/commands/workspace/test_create.py
git add tests/commands/setup/test_init.py tests/commands/workspace/test_create.py
```

### Step 3: Fix Parameter Names

```bash
# Replace renamed parameter
sed -i '' 's/global_config_ops=/global_config=/g' tests/commands/**/*.py
git add tests/commands/
```

### Step 4: Fix Constructor Calls

```bash
# Convert to factory method
sed -i '' 's/ErkContext(/ErkContext.for_test(/g' tests/commands/**/*.py
git add tests/commands/
```

### Step 5: Fix Hardcoded Paths

```bash
# Replace hardcoded test paths with env.cwd
sed -i '' 's|cwd=Path("/test/default/cwd")|cwd=env.cwd|g' tests/commands/**/*.py

# For isolated_filesystem tests, manually review and use:
# cwd=cwd (the local variable)
```

### Step 6: Run Tests and Iterate

```bash
# Run full CI suite
make all-ci

# Fix any remaining issues (see Troubleshooting below)

# Format code
uv run ruff format tests/

# Stage and continue
git add tests/
git rebase --continue
```

## Critical Knowledge

### ErkContext API Evolution

**OLD API** (❌ Don't use):

```python
test_ctx = ErkContext(
    git=git,
    global_config_ops=global_config_ops,  # ❌ Wrong parameter name
    cwd=Path("/test/default/cwd"),        # ❌ Hardcoded path
)
```

**NEW API** (✅ Use this):

```python
test_ctx = ErkContext.for_test(  # ✅ Factory method
    git=git,
    global_config=global_config,        # ✅ Renamed parameter
    cwd=env.cwd,                        # ✅ Actual environment path
)
```

**Why changed**:

- Parameter renamed: `global_config_ops` → `global_config` (clearer naming)
- Constructor now requires `local_config`, `repo`, `trunk_branch` parameters
- Factory method `.for_test()` provides sensible defaults
- Hardcoded paths forbidden (break in CI)

### Test Environment Patterns

#### Pattern 1: erk_isolated_fs_env (Preferred)

```python
from tests.test_utils.env_helpers import erk_isolated_fs_env

def test_something() -> None:
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # env provides: cwd, git_dir, root_worktree, erks_root

        git = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(erks_root=env.erks_root, ...)

        test_ctx = ErkContext.for_test(
            git=git,
            global_config=global_config,
            cwd=env.cwd,  # ✅ Use env.cwd
        )

        result = runner.invoke(cli, ["command"], obj=test_ctx)
```

#### Pattern 2: isolated_filesystem (Legacy)

```python
def test_something() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()  # ✅ Get actual current directory
        git_dir = cwd / ".git"
        git_dir.mkdir()

        git = FakeGit(git_common_dirs={cwd: git_dir})
        global_config = GlobalConfig(erks_root=cwd / "erks", ...)

        test_ctx = ErkContext.for_test(
            git=git,
            global_config=global_config,
            cwd=cwd,  # ✅ Use local cwd variable
        )

        result = runner.invoke(cli, ["command"], obj=test_ctx)
```

#### Pattern 3: NEVER Do This ❌

```python
# ❌ WRONG - Hardcoded path breaks in CI
test_ctx = ErkContext.for_test(
    cwd=Path("/test/default/cwd"),  # This path doesn't exist!
    ...
)
```

### SimulatedErkEnv Requirements

If you encounter a **local** `SimulatedErkEnv` class (defined in the test file, not imported):

```python
class SimulatedErkEnv:
    def __init__(self, root_worktree: Path, erks_root: Path) -> None:
        self.root_worktree = root_worktree
        self.erks_root = erks_root
        self.cwd = root_worktree  # ✅ Must have this attribute
        self._linked_worktrees: dict[str, Path] = {}

    def create_linked_worktree(self, name: str, branch: str, *, chdir: bool) -> Path:
        # ... create worktree ...

        if chdir:
            os.chdir(linked_wt)
            self.cwd = linked_wt  # ✅ Update cwd when changing directory

        return linked_wt
```

**Better solution**: Use centralized `env_helpers.py` instead of local class.

### BranchMetadata API

```python
from erk.core.branch_metadata import BranchMetadata

# ✅ Trunk branch
metadata = BranchMetadata.trunk(
    "main",
    children=["feature-1"],
    commit_sha="abc123"
)

# ✅ Feature branch
metadata = BranchMetadata.branch(
    "feature-1",
    "main",  # parent
    children=["feature-2"],
    commit_sha="def456"
)

# ❌ WRONG - No pr_number parameter
metadata = BranchMetadata.branch(
    "feature-1",
    "main",
    pr_number=123,  # ❌ This parameter doesn't exist!
    commit_sha="def456"
)

# ✅ Use FakeGitHubOps for PR data instead
github_ops = FakeGitHubOps(
    pr_statuses={"feature-1": ("OPEN", 123, "PR Title")}
)
```

## Troubleshooting

### ImportError: cannot import name 'erk_isolated_fs_env'

**Cause**: File `tests/test_utils/env_helpers.py` doesn't exist

**Solution**:

```bash
git show <commit>~1:tests/test_utils/env_helpers.py > tests/test_utils/env_helpers.py
git add tests/test_utils/env_helpers.py
```

**Why**: Rebasing commit X doesn't automatically include files added in parent commits

---

### TypeError: ErkContext.**init**() missing 3 required positional arguments

**Cause**: Direct constructor call instead of factory method

**Solution**:

```bash
sed -i '' 's/ErkContext(/ErkContext.for_test(/g' tests/commands/**/*.py
git add tests/commands/
```

---

### TypeError: got an unexpected keyword argument 'global_config_ops'

**Cause**: Parameter renamed

**Solution**:

```bash
sed -i '' 's/global_config_ops=/global_config=/g' tests/commands/**/*.py
git add tests/commands/
```

---

### FileNotFoundError: '/test/default/cwd'

**Cause**: Hardcoded path instead of actual environment path

**Solution**:

In `erk_isolated_fs_env`:

```python
# ❌ WRONG
cwd=Path("/test/default/cwd")

# ✅ RIGHT
with erk_isolated_fs_env(runner) as env:
    cwd=env.cwd
```

In `isolated_filesystem`:

```python
# ❌ WRONG
cwd=Path("/test/default/cwd")

# ✅ RIGHT
with runner.isolated_filesystem():
    cwd = Path.cwd()
    # ... use cwd variable
```

---

### AttributeError: 'SimulatedErkEnv' object has no attribute 'cwd'

**Cause**: Local `SimulatedErkEnv` class missing `cwd` attribute

**Solution**:

```python
class SimulatedErkEnv:
    def __init__(self, root_worktree: Path, erks_root: Path) -> None:
        self.root_worktree = root_worktree
        self.erks_root = erks_root
        self.cwd = root_worktree  # ✅ Add this line

    def create_linked_worktree(self, name: str, branch: str, *, chdir: bool) -> Path:
        # ...
        if chdir:
            os.chdir(linked_wt)
            self.cwd = linked_wt  # ✅ Add this line
```

**Better**: Use centralized `tests.test_utils.env_helpers.erk_isolated_fs_env` instead

---

### TypeError: BranchMetadata.branch() got unexpected keyword argument 'pr_number'

**Cause**: `pr_number` parameter doesn't exist in API

**Solution**:

```python
# ❌ WRONG
BranchMetadata.branch("feat", "main", pr_number=123, commit_sha="abc")

# ✅ RIGHT
BranchMetadata.branch("feat", "main", commit_sha="abc")

# Put PR data in FakeGitHubOps
github_ops = FakeGitHubOps(pr_statuses={"feat": ("OPEN", 123, "Title")})
```

---

### AssertionError: assert 'Expected Message' in result.output

**Cause**: Output message format changed

**Solution**:

```python
# Instead of checking exact message:
assert "Erks safe to delete:" in result.output  # ❌ Brittle

# Check for content/behavior:
assert "feature-1" in result.output  # ✅ More resilient
assert "merged" in result.output
assert "PR #123" in result.output
```

---

### make all-ci fails on format-check

**Cause**: File needs formatting

**Solution**:

```bash
uv run ruff format tests/
git add tests/
```

## Common Patterns

### Extract File from Git Commit

```bash
# From specific commit
git show <commit_hash>:path/to/file > path/to/file

# From parent of commit being rebased
git show <commit>~1:path/to/file > path/to/file

# Check what files are in commit
git ls-tree <commit> path/to/directory

# List changed files
git show <commit> --name-status
```

### Systematic Parameter Replacement

```bash
# Single file
sed -i '' 's/old_name=/new_name=/g' tests/file.py

# All Python files in directory
find tests -name "*.py" -exec sed -i '' 's/old_name=/new_name=/g' {} +

# Specific subdirectory
sed -i '' 's/old_name=/new_name=/g' tests/commands/**/*.py
```

### Context-Aware Path Fixing

Use this Python script when you need to fix paths based on context:

```python
#!/usr/bin/env python3
"""Fix cwd paths based on test context."""
from pathlib import Path

def fix_test_file(filepath: Path) -> None:
    content = filepath.read_text(encoding="utf-8")
    lines = content.split('\n')

    fixed_lines = []
    in_simulated_env = False
    in_isolated_fs = False

    for line in lines:
        # Track context
        if 'erk_isolated_fs_env(runner)' in line:
            in_simulated_env = True
            in_isolated_fs = False
        elif 'runner.isolated_filesystem()' in line:
            in_simulated_env = False
            in_isolated_fs = True

        # Fix based on context
        if 'cwd=env.cwd' in line and in_isolated_fs:
            line = line.replace('cwd=env.cwd', 'cwd=cwd')

        fixed_lines.append(line)

    filepath.write_text('\n'.join(fixed_lines), encoding="utf-8")

# Usage
fix_test_file(Path('tests/commands/graphite/test_land_stack.py'))
```

## File Locations

### Key Test Infrastructure Files

- **`tests/test_utils/env_helpers.py`**
  - Centralized simulated environment helper
  - Provides `erk_isolated_fs_env()` context manager
  - Added in commit `c6516290`

- **`tests/test_utils/builders.py`**
  - Test data builders (GraphiteCacheBuilder, PullRequestInfoBuilder, etc.)

- **`src/erk/core/context.py`**
  - `ErkContext` class
  - `ErkContext.for_test()` factory method

- **`src/erk/core/branch_metadata.py`**
  - `BranchMetadata` class
  - Factory methods: `.trunk()`, `.branch()`

### Configuration Classes

- **`GlobalConfig`** - Global configuration (not `ConfigStore`)
- **`LoadedConfig`** - Repository-specific configuration
- **`RepoContext`** - Repository context (root, name, erks_dir)

## Dependency Chain

Understanding commit dependencies is critical:

```
c6516290 - Adds tests/test_utils/env_helpers.py
    ↓
dfead85f - Migrates tests to use env_helpers.py
    ↓
01091d39 - Fixes issues in migrated tests
```

**Problem**: Rebasing only `01091d39` → Missing `env_helpers.py` from `c6516290`

**Solutions**:

1. Extract file from parent: `git show <commit>~1:path > path`
2. Rebase entire chain: `git rebase <base> <branch>~2` (include parents)

## Time Estimates

| Task                         | Without Guide | With Guide  | Speedup |
| ---------------------------- | ------------- | ----------- | ------- |
| Identify conflict type       | 5 min         | 1 min       | 5x      |
| Extract missing dependencies | 15 min        | 2 min       | 7.5x    |
| Fix parameter names          | 10 min        | 2 min       | 5x      |
| Fix constructor calls        | 15 min        | 2 min       | 7.5x    |
| Fix hardcoded paths          | 30 min        | 5 min       | 6x      |
| Fix local env class          | 10 min        | 3 min       | 3x      |
| Fix invalid parameters       | 5 min         | 1 min       | 5x      |
| Format and finish            | 5 min         | 2 min       | 2.5x    |
| **Total**                    | **~2 hours**  | **~15 min** | **8x**  |

## Prevention Strategies

### Before Rebasing

1. **Check commit dependencies**:

   ```bash
   git log --oneline <target>..<branch>
   ```

2. **Verify all files exist**:

   ```bash
   git show <commit> --name-status
   ```

3. **Consider rebasing entire chain** if commits are tightly coupled

### When Writing Tests

1. **Always use factory methods**: `ErkContext.for_test()`
2. **Never hardcode paths**: Use `env.cwd` or `Path.cwd()`
3. **Import from centralized helpers**: Don't create local `SimulatedErkEnv`
4. **Check parameter names**: Match current API (use IDE autocomplete)
5. **Test for behavior, not exact output**: Content over formatting

### Before Committing

1. **Run full CI**: `make all-ci`
2. **Format code**: `make format` or `uv run ruff format`
3. **Check for hardcoded paths**: `grep -r '"/test/' tests/`
4. **Verify imports**: `grep -r 'from tests.test_utils.env_helpers' tests/`

## Additional Resources

- **Test patterns**: [testing.md](testing.md)
- **Test infrastructure**: `tests/AGENTS.md`
- **Dignified Python**: Load `dignified-python-313` skill before editing
- **Codebase standards**: `AGENTS.md`

## Session Metadata

**Extracted from**: 2025-01-10 merge conflict resolution
**Total session time**: 2 hours
**Discovery time**: 1 hour 42 minutes (85%)
**Fix time**: 18 minutes (15%)
**Estimated time with this guide**: 10-15 minutes
**Speedup factor**: 8-12x

**Most valuable discoveries**:

1. Dependency extraction from parent commits (saved 20 min)
2. ErkContext evolution guide (saved 30 min)
3. Test environment patterns reference (saved 45 min)

---

_This document captures hard-won knowledge from actual conflict resolution. Keep it updated as the codebase evolves._
