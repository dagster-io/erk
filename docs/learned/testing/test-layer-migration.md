---
title: Test Layer Migration
read_when:
  - "moving tests between unit and integration layers"
  - "deciding whether a test belongs in unit or integration"
  - "test calls create_context() or uses real filesystem"
tripwires:
  - action: "unit test calling create_context() or scanning real filesystem"
    warning: "move to integration. Unit tests must use fakes only."
---

# Test Layer Migration

When to move tests between unit and integration layers, and how to do it.

## When to Migrate

Move a test from unit to integration when it:

- Calls real `create_context()` (performs real I/O, reads config files)
- Scans filesystem trees (reads directories, walks paths)
- Uses real git operations (creates repos, runs git commands)
- Depends on external tools being installed

## Migration Process

1. Identify tests that perform real I/O in unit layer
2. Move test file to `tests/integration/`
3. Verify no real I/O remains in the unit test directory
4. Ensure moved tests pass in integration suite (`make test-integration`)

## Example: test_forward_references.py

`test_forward_references.py` was moved from unit to integration because it called `create_context()` which performs real filesystem operations. Three context-dependent tests were extracted alongside it.

## Gateway Extension Pattern

When adding new gateway capabilities (e.g., codespace gateway extension), maintain the 5-place pattern:

1. **ABC** — abstract interface
2. **Real** — production implementation
3. **Fake** — test double with constructor injection
4. **Dry-run** — no-op implementation for `--dry-run`
5. **Printing** — human-readable output wrapper

Each new gateway method must be added to all five implementations.

## Related

- [Erk Test Reference](testing.md) — test fixtures and patterns
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) — 5-place implementation checklist
