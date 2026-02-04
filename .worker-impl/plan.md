# PR Address: Wrap constants behind @cache + update dignified-python

## Thread
- **Thread ID**: `PRRT_kwDOPxC3hc5sjCme`
- **File**: `src/erk/core/capabilities/codex_portable.py:36`
- **Request**: Wrap module-level constants behind `@functools.cache` functions; update dignified-python skill docs

## Changes

### 1. Convert constants to @cache functions

**File**: `src/erk/core/capabilities/codex_portable.py`

Convert:
```python
CODEX_PORTABLE_SKILLS: frozenset[str] = frozenset({...})
CLAUDE_ONLY_SKILLS: frozenset[str] = frozenset({...})
```

To:
```python
from functools import cache

@cache
def codex_portable_skills() -> frozenset[str]:
    return frozenset({...})

@cache
def claude_only_skills() -> frozenset[str]:
    return frozenset({...})
```

Note: Function names become `snake_case` (no longer UPPER_SNAKE_CASE since they're functions, not constants).

### 2. Update all callers (1 file)

**File**: `tests/unit/artifacts/test_codex_compatibility.py`

Update imports and usage:
- `from erk.core.capabilities.codex_portable import CLAUDE_ONLY_SKILLS, CODEX_PORTABLE_SKILLS`
  → `from erk.core.capabilities.codex_portable import claude_only_skills, codex_portable_skills`
- Replace all uses: `CODEX_PORTABLE_SKILLS` → `codex_portable_skills()`, `CLAUDE_ONLY_SKILLS` → `claude_only_skills()`

### 3. Update dignified-python module-design.md

**File**: `.claude/skills/dignified-python/references/module-design.md`

Update the "When Module-Level Constants ARE Acceptable" section (lines 83-92):
- Acceptable module-level: scalar primitives (int, str, bool, None) and tuples
- Must use `@cache` function: frozensets, dicts, lists, and any other mutable/complex collections
- Remove the `SUPPORTED_FORMATS = frozenset(...)` example from the "acceptable" section
- Add a new example showing frozenset behind `@cache`

## Verification

1. Run `uv run pytest tests/unit/artifacts/test_codex_compatibility.py -x -v`
2. Run `uv run ruff check` on changed `.py` files
3. Run `uv run ty check` on changed `.py` files