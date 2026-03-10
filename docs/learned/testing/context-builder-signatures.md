---
title: context_for_test() Dual Implementations
read_when:
  - "using context_for_test() in tests"
  - "choosing between erk-shared and src/erk test context"
  - "debugging TypeError from context_for_test()"
tripwires:
  - action: "using context_for_test() with wrong parameter name for issues"
    warning: "erk-shared uses github_issues= parameter, src/erk uses issues= parameter. These are NOT interchangeable — using wrong name causes TypeError."
---

# context_for_test() Dual Implementations

Two separate `context_for_test()` functions exist in the codebase. They have different parameter names and serve different test scopes.

## erk-shared Implementation

<!-- Source: packages/erk-shared/src/erk_shared/context/testing.py, context_for_test -->

**Location:** `packages/erk-shared/src/erk_shared/context/testing.py`

**Key parameter:** `github_issues=` (not `issues=`)

Always defaults to PlannedPRBackend. Used for isolated unit tests that only need erk-shared dependencies.

## src/erk Implementation

<!-- Source: tests/test_utils/test_context.py, context_for_test -->

**Location:** `tests/test_utils/test_context.py`

**Key parameter:** `issues=` (not `github_issues=`)

Has additional parameters for CLI-level dependencies (`console`, `shell`, `time`, `erk_installation`, `script_writer`, etc.). Uses `issues_explicitly_passed` detection for backwards compatibility.

## Decision Tree

| Test Type                             | Use                             | Import From                     |
| ------------------------------------- | ------------------------------- | ------------------------------- |
| Isolated unit tests (erk-shared only) | erk-shared `context_for_test()` | `erk_shared.context.testing`    |
| CLI/integration tests                 | src/erk `context_for_test()`    | `tests.test_utils.test_context` |
| Tests needing console, shell, time    | src/erk `context_for_test()`    | `tests.test_utils.test_context` |

## Common Mistake

Using `issues=` with the erk-shared version or `github_issues=` with the src/erk version causes a `TypeError` at runtime. The parameter names are intentionally different due to the different dependency scopes.
