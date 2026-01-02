---
steps:
  - name: "Add from __future__ import annotations to graphite/abc.py"
  - name: "Create tests/unit/test_forward_references.py with runtime import test"
  - name: "Add static analysis test for TYPE_CHECKING pattern detection"
  - name: "Run tests to verify they pass and would have caught this issue"
  - name: "Fix any other files the static analysis detects"
  - name: "Run full test suite to ensure no regressions"
---

# Fix Forward Reference Errors and Add Systematic Prevention

## Problem

Python 3.12 triggers `NameError` when:
1. Types are imported under `TYPE_CHECKING` (only available at type-check time)
2. Those types are used in annotations with `|` union syntax
3. The file lacks `from __future__ import annotations`

Without the future import, Python evaluates annotations at runtime, causing `NameError` for TYPE_CHECKING-only imports.

## Immediate Fix

**File**: `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py`

Add `from __future__ import annotations` after the docstring.

## Systematic Prevention: Two-Layer Testing

### Layer 1: Runtime Import Test (catches actual failures)

Create `tests/unit/test_forward_references.py` that:
1. Discovers all Python modules in `erk` and `erk_shared` packages via filesystem traversal
2. Imports each module using `importlib.import_module()`
3. Fails with helpful message if `NameError` occurs

This catches any forward reference issue that manifests at import time (which is all of them for class/function definitions).

### Layer 2: Static Analysis Test (catches the pattern proactively)

Add a second test that uses AST parsing to detect the risky pattern:
1. Find all Python files
2. Parse each file's AST
3. Detect files that have:
   - Imports under `if TYPE_CHECKING:` block
   - NO `from __future__ import annotations`
4. Fail with list of files that should add the future import

This catches the pattern even before it causes a runtime error, providing early warning.

```python
def test_files_with_type_checking_imports_have_future_annotations() -> None:
    """Detect files using TYPE_CHECKING imports without future annotations.

    This is a proactive check - files matching this pattern WILL break
    on some Python versions even if they don't break on the current one.
    """
    violations = []
    for filepath in discover_python_files():
        if has_type_checking_imports(filepath) and not has_future_annotations(filepath):
            violations.append(filepath)

    if violations:
        pytest.fail(
            f"Files with TYPE_CHECKING imports missing 'from __future__ import annotations':\n"
            + "\n".join(f"  - {f}" for f in violations)
        )
```

## Implementation Steps

1. Add `from __future__ import annotations` to `graphite/abc.py`
2. Create `tests/unit/test_forward_references.py` with both tests:
   - `test_all_modules_import_successfully()` - runtime validation
   - `test_files_with_type_checking_have_future_annotations()` - static pattern detection
3. Run the tests to verify they pass (and would have caught this issue)
4. Fix any other files the static analysis detects
5. Run full test suite to ensure no regressions

## Files to Modify

- `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py` - Add future annotations import
- `tests/unit/test_forward_references.py` - New test file with both layers

## Why Two Layers?

- **Runtime test**: Catches real failures, Python-version specific
- **Static test**: Catches the risky pattern proactively, regardless of Python version
- Together they ensure both current breakage is caught AND future breakage is prevented

## Related Documentation

- `dignified-python` skill - Python coding standards
- `fake-driven-testing` skill - Test placement guidelines