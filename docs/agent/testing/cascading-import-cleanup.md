---
title: Cascading Import Cleanup Guide
read_when:
  - "removing modules from codebase"
  - "import errors after module deletion"
  - "cleaning up removed functionality"
---

# Cascading Import Cleanup Guide

This guide documents the systematic process for removing modules from the codebase and handling cascading import errors.

## The Problem

When you delete a Python module, you often trigger cascading import failures:

```
Round 1: Delete module.py
Round 2: Fix __init__.py that imported module
Round 3: Fix tests that imported from __init__
Round 4: Fix mocks that referenced the module
Round 5: Fix type stubs if any
```

## Systematic Removal Process

### Step 1: Identify All Imports

Before deleting, find all imports of the target module:

```bash
# Find all imports of module_name
grep -r "from my_package import module_name" .
grep -r "from my_package.module_name import" .
grep -r "import my_package.module_name" .
```

### Step 2: Create Removal Checklist

For each module being removed, track:

- [ ] Main module file deleted
- [ ] Package `__init__.py` updated
- [ ] Test files updated
- [ ] Mock/fake files updated
- [ ] Type stubs updated (if any)
- [ ] Documentation updated

### Step 3: Delete in Dependency Order

Remove files in order from "most dependent" to "least dependent":

```
1. Tests (depend on everything)
2. Mocks/Fakes (depend on interfaces)
3. Implementation (depends on interfaces)
4. __init__.py exports (exposes modules)
5. Main module file
```

### Step 4: Iterative Cleanup

After each deletion round, run tests to find next failures:

```bash
# Run tests, capture failures
pytest --tb=short 2>&1 | grep "ImportError\|ModuleNotFoundError"

# Fix each import error
# Repeat until tests pass
```

## Example: Removing `bypass_pr` Commands

This example shows removing the bypass PR commands (`pr-prep`, `pr-update`, `prepare-local`):

### Round 1: Delete Command Files

```bash
rm src/erk/commands/pr_prep.py
rm src/erk/commands/pr_update.py
rm src/erk/commands/prepare_local.py
```

### Round 2: Fix `__init__.py`

```python
# Before
from erk.commands.pr_prep import pr_prep
from erk.commands.pr_update import pr_update
from erk.commands.prepare_local import prepare_local

# After (remove the lines)
```

### Round 3: Fix Test Imports

```python
# Before
from erk.commands import pr_prep, pr_update

# After (remove the imports and associated tests)
```

### Round 4: Fix Mock References

```python
# Before
class FakeCommands:
    pr_prep = MagicMock()
    pr_update = MagicMock()

# After (remove the mock attributes)
```

## Anti-Patterns

### DON'T: Delete Everything at Once

```bash
# BAD: Deletes everything, hard to debug failures
rm -rf src/my_module tests/test_my_module
pytest  # 47 failures, good luck!
```

### DO: Delete Incrementally

```bash
# GOOD: One thing at a time
rm src/my_module/feature.py
pytest  # 3 failures
# Fix the 3 failures
pytest  # Pass!
# Continue with next file
```

### DON'T: Leave Dead Imports

```python
# BAD: Import exists but module deleted
try:
    from my_package import deleted_module
except ImportError:
    deleted_module = None  # Gross!
```

### DO: Remove Cleanly

```python
# GOOD: No trace of deleted module
# (The import line is simply gone)
```

## Troubleshooting

### Circular Import After Removal

If removing a module creates circular imports:

1. The module may have been breaking a cycle
2. Identify the cycle with `importlib` debugging
3. Restructure imports or move code

### Test Discovery Fails

If pytest can't discover tests after removal:

1. Check `__init__.py` files for syntax errors
2. Look for dangling relative imports
3. Verify `conftest.py` doesn't import deleted modules

## Related Documentation

- [Import Conflict Resolution](import-conflict-resolution.md)
- [Testing Standards](testing.md)
