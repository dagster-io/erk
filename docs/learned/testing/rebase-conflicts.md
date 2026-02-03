---
title: Erk Test Rebase Conflicts
last_audited: "2026-02-03"
audit_result: edited
read_when:
  - "fixing merge conflicts in erk tests"
  - "ErkContext API changes during rebase"
  - "env_helpers conflicts"
---

# Erk Test Rebase Conflicts

**For generic merge conflict resolution**: Use the `/erk:fix-conflicts` command.

This document covers **erk-specific test patterns** you'll encounter during rebases: ErkContext API evolution, env_helpers, parameter renames.

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

**Common missing file**: `tests/test_utils/env_helpers.py`

### Step 2: Resolve Conflicts

For test infrastructure conflicts, accept the incoming version (newer pattern):

```bash
# Accept incoming version of conflicted files
git show <incoming_commit>:<path/to/conflicted/file> > <path/to/conflicted/file>
git add <path/to/conflicted/file>
```

### Step 3: Fix Parameter Names

```bash
# Replace renamed parameter (if migrating from old code)
sed -i '' 's/global_config_ops=/global_config=/g' tests/commands/**/*.py
git add tests/commands/
```

### Step 4: Fix Constructor Calls

The preferred test factory is `context_for_test()` from `src/erk/core/context.py`. There is also `ErkContext.for_test()` on the class itself (defined in `erk_shared`), but it has a more limited parameter set. Most CLI tests should use `context_for_test()`.

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

### ErkContext Test Construction

There are two factory approaches for creating test contexts:

**1. `context_for_test()` (preferred for CLI tests)** -- defined in `src/erk/core/context.py`:

```python
from erk.core.context import context_for_test

test_ctx = context_for_test(
    git=git,
    global_config=global_config,
    cwd=env.cwd,
)
```

This function accepts all ErkContext fields as optional keyword arguments and fills in sensible fake defaults for anything not provided.

**2. `ErkContext.for_test()` (limited parameter set)** -- defined in `erk_shared/context/context.py`:

```python
test_ctx = ErkContext.for_test(
    git=git,
    cwd=env.cwd,
)
```

This static method accepts a smaller set of parameters (`github_issues`, `git`, `github`, `claude_installation`, `prompt_executor`, `debug`, `repo_root`, `cwd`, `repo_info`). It does NOT accept `global_config`.

**When to use which:**

| Scenario | Use | Why |
|---|---|---|
| CLI command tests needing `global_config` | `context_for_test()` | Only factory that accepts `global_config` |
| CLI command tests with `erk_isolated_fs_env` | `env.build_context()` | Wraps `context_for_test()` with env defaults |
| Tests in `erk_shared` or without `global_config` needs | `ErkContext.for_test()` | Available without depending on `erk.core` |
| Default choice for most tests | `context_for_test()` | Broadest parameter set, fills in fake defaults |

**Key points**:

- `GlobalConfig` uses `erk_root` (not `erks_root`)
- Constructor requires many parameters; always use a factory function for tests
- Hardcoded paths like `Path("/test/default/cwd")` are forbidden (break in CI)

### Test Environment Patterns

#### Pattern 1: erk_isolated_fs_env (Preferred)

```python
from tests.test_utils.env_helpers import erk_isolated_fs_env

def test_something() -> None:
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # env provides: cwd, git_dir, root_worktree, erk_root, etc.

        git = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = context_for_test(
            git=git,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["command"], obj=test_ctx)
```

#### Pattern 2: isolated_filesystem (Legacy)

```python
def test_something() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        git = FakeGit(git_common_dirs={cwd: git_dir})

        test_ctx = context_for_test(
            git=git,
            cwd=cwd,
        )

        result = runner.invoke(cli, ["command"], obj=test_ctx)
```

#### Pattern 3: NEVER Do This

```python
# WRONG - Hardcoded path breaks in CI
test_ctx = context_for_test(
    cwd=Path("/test/default/cwd"),  # This path doesn't exist!
    ...
)
```

## Troubleshooting

### ImportError: cannot import name 'erk_isolated_fs_env'

**Cause**: File `tests/test_utils/env_helpers.py` doesn't exist in current rebase state

**Solution**:

```bash
git show <commit>~1:tests/test_utils/env_helpers.py > tests/test_utils/env_helpers.py
git add tests/test_utils/env_helpers.py
```

**Why**: Rebasing commit X doesn't automatically include files added in parent commits

---

### TypeError: ErkContext.**init**() missing required positional arguments

**Cause**: Direct constructor call instead of factory function

**Solution**: Use `context_for_test()` from `erk.core.context` or `ErkContext.for_test()`.

---

### TypeError: got an unexpected keyword argument 'global_config_ops'

**Cause**: Parameter renamed to `global_config`

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
# WRONG
cwd=Path("/test/default/cwd")

# RIGHT
with erk_isolated_fs_env(runner) as env:
    cwd=env.cwd
```

In `isolated_filesystem`:

```python
# WRONG
cwd=Path("/test/default/cwd")

# RIGHT
with runner.isolated_filesystem():
    cwd = Path.cwd()
    # ... use cwd variable
```

---

### AssertionError: assert 'Expected Message' in result.output

**Cause**: Output message format changed

**Solution**:

```python
# Instead of checking exact message:
assert "Erks safe to delete:" in result.output  # Brittle

# Check for content/behavior:
assert "feature-1" in result.output  # More resilient
assert "merged" in result.output
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

## File Locations

### Key Test Infrastructure Files

- **`tests/test_utils/env_helpers.py`**
  - Centralized simulated environment helper
  - Provides `erk_isolated_fs_env()` and `erk_inmem_env()` context managers

- **`tests/test_utils/builders.py`**
  - Test data builders (GraphiteCacheBuilder, PullRequestInfoBuilder, etc.)

- **`src/erk/core/context.py`**
  - `context_for_test()` factory function (preferred for CLI tests)
  - Re-exports `ErkContext` from `erk_shared`

- **`packages/erk-shared/src/erk_shared/context/context.py`**
  - `ErkContext` class definition
  - `ErkContext.for_test()` static method (limited parameter set)

### Configuration Classes

- **`GlobalConfig`** -- Global configuration (`erk_root`, `use_graphite`, etc.)
- **`LoadedConfig`** -- Merged repo + project configuration
- **`RepoContext`** -- Repository context (`root`, `repo_name`, `worktrees_dir`, `main_repo_root`)

## Dependency Chain

Understanding commit dependencies is critical when rebasing:

**Problem**: Rebasing only a child commit without its parent commits can leave missing files.

**Solutions**:

1. Extract file from parent: `git show <commit>~1:path > path`
2. Rebase entire chain: `git rebase <base> <branch>~2` (include parents)

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

1. **Always use factory functions**: `context_for_test()` or `ErkContext.for_test()`
2. **Never hardcode paths**: Use `env.cwd` or `Path.cwd()`
3. **Import from centralized helpers**: Use `erk_isolated_fs_env` from `tests.test_utils.env_helpers`
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
- **Dignified Python**: Load `dignified-python` skill before editing
- **Codebase standards**: `AGENTS.md`

## Session Metadata

**Extracted from**: 2025-01-10 merge conflict resolution

**Most valuable discoveries**:

1. Dependency extraction from parent commits
2. ErkContext evolution guide
3. Test environment patterns reference

---

_This document captures hard-won knowledge from actual conflict resolution. Keep it updated as the codebase evolves._
