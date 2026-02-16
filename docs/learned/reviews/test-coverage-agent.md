---
title: Test Coverage Review Agent
read_when:
  - modifying test-coverage review agent prompt
  - adding new legitimately untestable file patterns
  - debugging false positives in test coverage review
tripwires:
  - action: "flagging code as untested in PR review"
    warning: "Check if the file is legitimately untestable first. The 5-layer architecture defines which layers need tests — Layers 0-2 (CLI wrappers, type-only files, ABCs) are excluded. See .github/reviews/test-coverage.md for the full detection logic."
  - action: "adding a new untestable file category"
    warning: "New categories must align with the 5-layer test architecture. Only files in Layers 0-2 qualify. If the file contains any business logic (Layer 3+), it requires tests regardless of how thin the logic appears."
last_audited: "2026-02-08 00:00 PT"
audit_result: edited
---

# Test Coverage Review Agent

<!-- Source: .github/reviews/test-coverage.md -->

This review agent enforces a key design decision: **which source files require tests and which don't**. The answer comes from mapping erk's 5-layer test architecture onto PR diffs — not from line-count heuristics or coverage percentages.

## Why "Legitimately Untestable" Exists

The central insight is that erk's architecture _intentionally_ creates files that carry no testable logic. These fall into Layers 0-2 of the test architecture:

| Architecture Layer         | File Type                                                            | Why No Tests Needed                     |
| -------------------------- | -------------------------------------------------------------------- | --------------------------------------- |
| Layer 0 — Wiring           | `__init__.py`, `conftest.py`, `__main__.py`                          | Pure infrastructure, no logic           |
| Layer 1 — Thin CLI         | Click-decorated functions that only delegate                         | Testing these would test Click, not erk |
| Layer 2 — Type definitions | `TypeVar`, `Protocol`, type aliases, ABCs with only abstract methods | No runtime behavior to verify           |

Everything at Layer 3 (business logic) and Layer 4 (operations/orchestration) requires tests — the agent flags files in these layers that lack corresponding test files.

This isn't a convenience shortcut. It enforces the architectural boundary: if a "thin CLI wrapper" starts accumulating business logic, the agent will correctly flag it as needing tests, which signals that the logic should be extracted to a testable layer.

## Design Decisions

**Haiku for categorization**: The agent uses `claude-haiku-4-5` because its work is mechanical — file bucketing, pattern matching, diff reading. Categorizing files into 6 buckets doesn't benefit from deeper reasoning, and haiku keeps review times fast across large PRs.

**Significant modification filtering**: Not all source file changes need test updates. The agent reads diffs to distinguish significant changes (new functions, classes, logic) from cosmetic ones (import reordering, type annotations, formatting). This prevents false positives on cleanup PRs that touch many files without changing behavior.

**Test matching is name-based, not import-based**: The primary match strategy uses file naming conventions (`test_<filename>.py`, `test_<parent>_<filename>.py`) rather than import analysis. Import-based matching is the fallback for newly added test files only. This keeps the agent fast and predictable — agents debugging false positives should check file naming first.

## Debugging False Positives

When the agent incorrectly flags a file as needing tests:

1. **Is it actually Layer 0-2?** Read the file — if it contains only Click decorators delegating elsewhere, only type definitions, or only abstract methods, it should be detected as untestable. If detection fails, the file may have accumulated logic that crossed the layer boundary.

2. **Is the test file named correctly?** The agent expects `test_<filename>.py` or `test_<parent>_<filename>.py` under `tests/`. Non-standard test file names won't be matched.

3. **Is the modification truly significant?** If only imports or type annotations changed, the agent should early-exit. Check whether the diff contains actual logic changes.

**Anti-pattern**: Adding a file to an exclusion list to silence the agent when the file actually contains business logic. The correct fix is to extract the logic to a testable module.

## Related Documentation

- [Convention-Based Reviews](../ci/convention-based-reviews.md) — Review system that discovers and runs this agent
- [Testing Reference](../testing/testing.md) — Full 5-layer test architecture
- [Testing Tripwires](../testing/tripwires.md) — Test-related constraints
