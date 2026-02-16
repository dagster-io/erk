---
description: Converting tests from monkeypatch to parameter injection for testability
read_when:
  - adding parameters to functions for testability
  - refactoring functions to accept dependencies as parameters
  - encountering monkeypatch AttributeError after import removal
tripwires:
  - action: "adding required parameters to functions called by tests"
    warning: "Grep ALL call sites in src/ and tests/ before implementation. Convert direct callers to parameter injection, retarget CLI test patches to import location."
  - action: "removing imports from a module"
    warning: "Grep test files for monkeypatch statements targeting that module. All patches must be converted to parameter injection or retargeted."
last_audited: "2026-02-16 00:00 PT"
audit_result: new
---

# Parameter Injection Testing Pattern

## Overview

When adding parameters to functions to improve testability, tests must be updated to use parameter injection rather than monkeypatching. This pattern is more explicit and less brittle than patching module imports.

## Two-Phase Refactoring Strategy

### Phase 1: Direct Callers

Tests that call the function directly should pass parameters explicitly.

<!-- Source: tests/unit/artifacts/test_orphans.py -->
<!-- Source: tests/unit/artifacts/test_missing.py -->

See test files in `tests/unit/artifacts/` for examples - these tests pass `bundled_claude_dir` and `bundled_skills_dir` directly to `find_orphaned_artifacts()` and `find_missing_artifacts()`.

### Phase 2: CLI Tests

Tests that invoke functions through CLI commands cannot pass parameters directly (the CLI calls internal functions). These tests legitimately need monkeypatching, but patches must target the correct import location.

**Critical**: Patches target the import location (call site), not the definition site.

<!-- Source: tests/unit/cli/commands/artifact/test_cli.py -->

See `test_cli.py` patching `erk.cli.commands.artifact.check.get_bundled_claude_dir` (import location) not `erk.artifacts.artifact_health.get_bundled_claude_dir` (definition).

## Scope Discovery Before Implementation

Before changing function signatures:

1. Grep ALL call sites: `grep "function_name(" src/ tests/`
2. Identify which tests call directly vs through CLI
3. Create a complete list of files needing updates
4. Plan Phase 1 and Phase 2 updates separately
