# Plan: Objective #9272 Nodes 1.1–1.2 — Create erk-slots Package + Conditional Loading

## Context

Objective #9272 extracts the slot/pool system into a separate workspace package. Nodes 1.1 and 1.2 establish the package structure and conditional loading — the foundation for all subsequent extraction work.

**Node 1.1**: Create `packages/erk-slots/` workspace package
**Node 1.2**: Conditional plugin loading in cli.py

## Implementation

### 1. Create `packages/erk-slots/` package

Create the standard workspace package layout:

```
packages/erk-slots/
├── pyproject.toml
├── README.md
└── src/erk_slots/
    └── __init__.py
```

**`pyproject.toml`** — follow erk-statusline pattern:
```toml
[project]
name = "erk-slots"
version = "0.9.11"
description = "Worktree pool slot management for erk"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "erk-shared",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/erk_slots"]
```

**`src/erk_slots/__init__.py`** — re-export `slot_group` from existing code for now:
```python
"""Worktree pool slot management plugin for erk."""

from erk.cli.commands.slot import slot_group

__all__ = ["slot_group"]
```

Note: This initial version imports from `erk.cli.commands.slot` — the code hasn't moved yet (that's node 1.3). This PR just establishes the package boundary and conditional loading. The `__init__.py` acts as a thin re-export layer that will become the real home in node 1.3.

### 2. Register in root `pyproject.toml`

Four places to update in `/Users/schrockn/code/erk/pyproject.toml`:

1. **Line 2–7** — Add `"packages/erk-slots"` to `[tool.uv.workspace]` members
2. **Line 9–13** — Add `erk-slots = { workspace = true }` to `[tool.uv.sources]`
3. **Line 117** — Add `"erk_slots"` to `[tool.ruff.lint.isort]` known-first-party
4. **Line 120** — Add `"packages/erk-slots/src"` to `[tool.ty.src]` include
5. **Line 133** — Add `"packages/erk-slots/tests"` to `[tool.pytest.ini_options]` testpaths

### 3. Make slot loading conditional in `cli.py`

**Remove** (line 36):
```python
from erk.cli.commands.slot import slot_group
```

**Remove** (line 208):
```python
cli.add_command(slot_group)
```

**Add** conditional block (after the existing learned-docs conditional, ~line 220):
```python
try:
    from erk_slots import slot_group
    cli.add_command(slot_group)
except ImportError:
    pass
```

This is simpler than the `is_learned_docs_available` pattern because the check is just "is the package installed?" — a try/except ImportError is the standard Python idiom for optional dependencies.

**File**: `src/erk/cli/cli.py`

### 4. Run `uv sync` to install the new package

After creating the package, run `uv sync` to install `erk-slots` in the workspace so the import works.

## Files Modified

| File | Change |
|------|--------|
| `packages/erk-slots/pyproject.toml` | New — package definition |
| `packages/erk-slots/README.md` | New — brief description |
| `packages/erk-slots/src/erk_slots/__init__.py` | New — re-exports slot_group |
| `pyproject.toml` | Add erk-slots to workspace, isort, ty, pytest |
| `src/erk/cli/cli.py` | Replace hardcoded slot import with try/except from erk_slots |

## Verification

1. `uv sync` succeeds — erk-slots installs in workspace
2. `erk slot list` works — slot group loads from erk_slots package
3. `erk --help` shows `slot` subcommand
4. `python -c "from erk_slots import slot_group; print(slot_group.name)"` prints "slot"
5. Run existing slot tests — they should still pass since the code hasn't moved, just the import path for cli.py changed
6. Run `make fast-ci` to verify nothing broke
