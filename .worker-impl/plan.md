# Plan: Consolidate Dual FakeGit Implementations

## Problem

Two independent FakeGit implementations exist:
1. **Primary** (`packages/erk-shared/src/erk_shared/git/fake.py`) - 827 lines, complete, used by 50+ files
2. **Legacy** (`tests/fakes/git.py`) - 707 lines, simpler, only used by 1 file

This caused debugging issues when only one implementation was updated.

## Analysis

The legacy `tests/fakes/git.py` is only imported in ONE place:
- `tests/commands/test_implement.py:12` - `from tests.fakes.git import FakeGit`

The primary implementation in `erk_shared` is:
- More complete (symlink handling, advanced constructor params)
- Used by all other test files (50+)
- Has proper mutation tracking initialization

## Recommended Approach

**Keep**: `packages/erk-shared/src/erk_shared/git/fake.py` (the complete implementation)
**Delete**: `tests/fakes/git.py` (the legacy implementation)

## Implementation Steps

### Step 1: Update the single import in test_implement.py
Change:
```python
from tests.fakes.git import FakeGit
```
To:
```python
from erk_shared.git.fake import FakeGit
```

### Step 2: Delete the legacy FakeGit file
```
tests/fakes/git.py
```

### Step 3: Update documentation references
The following documentation files reference `tests.fakes.git` in examples. Update them to use `erk_shared.git.fake`:

- `docs/agent/testing/testing.md:52` - Example import (references `tests.fakes.gitops` which may be different)
- `.claude/skills/erk/references/erk.md:1119` - Example import
- `tests/AGENTS.md:52` - Example explaining namespace packages
- `tests/unit/AGENTS.md:13` - Example explaining namespace packages
- `tests/unit/fakes/AGENTS.md:12` - Example explaining namespace packages

### Step 4: Run tests to verify
```bash
uv run pytest tests/commands/test_implement.py -v
uv run pytest tests/ -k "git" --collect-only  # Verify no import errors
```

## Files to Modify

| File | Action |
|------|--------|
| `tests/commands/test_implement.py` | Update import |
| `tests/fakes/git.py` | DELETE |
| `docs/agent/testing/testing.md` | Update example |
| `.claude/skills/erk/references/erk.md` | Update example |
| `tests/AGENTS.md` | Update example |
| `tests/unit/AGENTS.md` | Update example |
| `tests/unit/fakes/AGENTS.md` | Update example |

## Verification

1. Tests pass: `uv run pytest tests/commands/test_implement.py`
2. No import errors: `uv run pytest tests/ --collect-only`
3. Type checking passes: `uv run pyright`

## Skills to Load Before Implementation

- `dignified-python-313` - For Python code standards (already loaded via hooks)
- `fake-driven-testing` - For testing patterns (already loaded)