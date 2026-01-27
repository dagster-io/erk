---
title: Gateway Consolidation Checklist
read_when:
  - "moving gateways to gateway/ directory"
  - "consolidating gateway packages"
  - "performing systematic refactoring"
---

# Gateway Consolidation Checklist

Systematic checklist for consolidating gateway packages into the `gateway/` directory structure.

## Overview

Gateway consolidation moves gateway packages from scattered locations into a unified `packages/erk-shared/src/erk_shared/gateway/` directory. This improves discoverability and maintains consistent structure.

## Consolidation Steps

### 1. Identify Gateway Package

Confirm the package follows the standard gateway pattern:

- Has `abc.py` with abstract interface
- Has `real.py` with production implementation
- Has `fake.py` with test implementation
- May have `dry_run.py` and/or `printing.py` wrappers
- Has `__init__.py` with re-exports

### 2. Create Target Directory

```bash
mkdir -p packages/erk-shared/src/erk_shared/gateway/<gateway-name>/
```

**Naming:** Use snake_case for directory name (e.g., `command_executor`, `branch_manager`).

### 3. Move Files

Use `git mv` to preserve history:

```bash
# Example: moving CommandExecutor
git mv packages/erk-shared/src/erk_shared/tui/commands/executor.py \
       packages/erk-shared/src/erk_shared/gateway/command_executor/abc.py

git mv packages/erk-shared/src/erk_shared/tui/commands/real_executor.py \
       packages/erk-shared/src/erk_shared/gateway/command_executor/real.py

git mv packages/erk-shared/src/erk_shared/tui/commands/fake_executor.py \
       packages/erk-shared/src/erk_shared/gateway/command_executor/fake.py
```

**Important:** If files don't match standard naming (e.g., `executor.py` instead of `abc.py`), rename during the move.

### 4. Update Imports in Moved Files

Update relative imports within the gateway package:

**Before:**
```python
from erk_shared.tui.commands.executor import CommandExecutor
```

**After:**
```python
from erk_shared.gateway.command_executor.abc import CommandExecutor
```

### 5. Create __init__.py

Add `__init__.py` with re-exports for clean imports:

```python
"""CommandExecutor gateway package."""

from erk_shared.gateway.command_executor.abc import CommandExecutor
from erk_shared.gateway.command_executor.fake import FakeCommandExecutor
from erk_shared.gateway.command_executor.real import RealCommandExecutor

__all__ = ["CommandExecutor", "FakeCommandExecutor", "RealCommandExecutor"]
```

### 6. Update All Import Sites

Find all files that import the gateway:

```bash
grep -r "from erk_shared.tui.commands.executor" packages/ src/
```

Update systematically using LibCST or manual editing:

**Before:**
```python
from erk_shared.tui.commands.executor import CommandExecutor
from erk_shared.tui.commands.real_executor import RealCommandExecutor
```

**After:**
```python
from erk_shared.gateway.command_executor import CommandExecutor, RealCommandExecutor
```

See [LibCST Systematic Imports](../refactoring/libcst-systematic-imports.md) for automated refactoring.

### 7. Run Linter

Fix any import sorting or formatting issues:

```bash
ruff check --fix packages/erk-shared/src/erk_shared/gateway/<gateway-name>/
ruff check --fix packages/ src/  # Fix all import sites
```

### 8. Run Tests

Verify tests still pass:

```bash
pytest tests/unit/ -k <gateway-name>
pytest tests/integration/ -k <gateway-name>
```

### 9. Update Documentation

- Add entry to `docs/learned/architecture/gateway-inventory.md`
- Update any existing gateway-specific documentation with new paths
- Update `docs/learned/architecture/index.md` if needed

### 10. Create Pull Request

Commit with descriptive message:

```bash
git add .
git commit -m "Move <GatewayName> gateway to gateway/ directory

Consolidates <GatewayName> into unified gateway structure:
- Moved from packages/erk-shared/src/erk_shared/<old-path>/
- Updated imports across codebase
- Added __init__.py for clean re-exports"

git push
gh pr create --fill
```

## Common Issues

### Import Sorting Violations

**Symptom:** Ruff reports I001 violations after moving files.

**Fix:** Run `ruff check --fix` on affected files.

### Circular Import Errors

**Symptom:** `ImportError: cannot import name 'X' from partially initialized module`

**Cause:** Gateway ABC imports types from moved modules.

**Fix:** Use `TYPE_CHECKING` guard:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erk_shared.gateway.other_gateway import OtherType
```

### Test Failures from Stale Imports

**Symptom:** Tests fail with `ModuleNotFoundError`

**Cause:** Test files still use old import paths.

**Fix:** Update test imports to match new paths.

### Missing __init__.py

**Symptom:** `ModuleNotFoundError: No module named 'erk_shared.gateway.X'`

**Cause:** Forgot to create `__init__.py` in new directory.

**Fix:** Create `__init__.py` with re-exports.

## Batch Operations

For consolidating multiple gateways in one PR:

1. Move all gateways first (preserve history)
2. Update imports for all gateways together (use LibCST)
3. Run ruff fix once at the end
4. Run full test suite

This reduces the number of intermediate broken states.

## Related Topics

- [Gateway Inventory](../architecture/gateway-inventory.md) - Current gateway catalog
- [LibCST Systematic Imports](../refactoring/libcst-systematic-imports.md) - Automated refactoring
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) - Gateway structure
