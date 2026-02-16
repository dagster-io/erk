---
description: Strategy for updating tests when changing function signatures
read_when:
  - adding parameters to functions
  - refactoring function signatures
  - test failures after signature changes
tripwires:
  - action: "changing function signatures"
    warning: "Grep ALL call sites before changing signatures. Convert direct callers to injection, retarget CLI test patches."
last_audited: "2026-02-16 00:00 PT"
audit_result: new
---

# Two-Phase Test Refactoring Strategy

## Overview

When changing function signatures, tests require different treatment based on how they call the function.

## Phase 1: Direct Callers

Tests that call the function directly - convert to parameter injection.

```python
# Before: monkeypatch
mocker.patch("erk.artifacts.artifact_health.get_bundled_claude_dir")

# After: parameter injection
find_orphaned_artifacts(bundled_claude_dir=tmp_path / ".claude")
```

## Phase 2: CLI/Integration Tests

Tests that invoke through CLI - retarget patches to import location.

```python
# Patch where function is IMPORTED (call site)
mocker.patch("erk.cli.commands.artifact.check.get_bundled_claude_dir")

# NOT where it's DEFINED (source)
mocker.patch("erk.artifacts.artifact_health.get_bundled_claude_dir")  # WRONG
```

## Scope Discovery

Before implementation:

1. `grep "function_name(" src/ tests/` - find all callers
2. Categorize: direct calls vs CLI/integration
3. Plan Phase 1 and Phase 2 updates separately
