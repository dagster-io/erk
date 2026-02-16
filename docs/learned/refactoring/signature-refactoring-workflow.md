---
title: Signature Refactoring Workflow
read_when:
  - changing function signatures with multiple call sites
  - adding parameters to public functions
  - systematic refactoring across multiple files
tripwires:
  - action: "changing function signature without grepping for call sites first"
    warning: "Always grep for all call sites before signature changes - use Grep to find `function_name(`"
---

# Signature Refactoring Workflow

Systematic approach to changing function signatures with multiple call sites.

## Six-Phase Process

**Phase 1: Discovery**
Grep for all call sites before making changes:

```bash
Grep(pattern="function_name\\(", path="src/")
Grep(pattern="function_name\\(", path="tests/")
```

**Phase 2: Modify Function Signatures**
Add parameters, update function body, remove internal calls.

**Phase 3: Update Production Callers**
Update all production call sites (CLI commands, other modules).

**Phase 4: Update Direct Test Calls**
Tests calling functions directly use parameter injection.

**Phase 5: Update CLI Test Patches**
CLI integration tests update monkeypatch targets to boundary modules.

**Phase 6: Cleanup**

- Remove unused imports
- Run ty, ruff, pytest to verify

## Key Insight

Tests require two-tier updates:

1. **Direct calls**: Use parameter injection (cleaner)
2. **CLI tests**: Update patch targets (patches at boundary)

## Example

PR #7135 followed this workflow for three functions across 4 call sites in 2 production files and tests in 4 test files.

## Related

- [Parameter Injection Pattern](../testing/parameter-injection-pattern.md) - Testing pattern details
- [Dependency Injection Boundaries](../architecture/dependency-injection-boundaries.md) - Architectural context
