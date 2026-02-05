---
title: Test Coverage Review Agent
read_when:
  - "modifying test-coverage review agent"
  - "understanding test coverage review logic"
  - "adding legitimately untestable file patterns"
  - "debugging false positives in test coverage review"
tripwires:
  - action: "flagging code as untested in PR review"
    warning: "Check if file is legitimately untestable first. CLI wrappers (only Click decorators), type-only files (TypeVar/Protocol/type aliases), and ABC interfaces (only abstract methods) should be excluded from test coverage requirements."
last_audited: "2026-02-05 13:56 PT"
audit_result: edited
---

# Test Coverage Review Agent

Automated review agent that analyzes test coverage for Python source files in PRs. Runs via the convention-based review system on every PR.

## Source Definition

The agent prompt is defined in `.github/reviews/test-coverage.md`. Consult that file for full implementation details including:

- 6-bucket file categorization (source_added/modified/deleted, tests_added/modified/deleted)
- Excluded file patterns (`__init__.py`, `conftest.py`, type stubs, config files)
- Legitimately untestable file detection (thin CLI wrappers, type-only files, ABCs, re-export files)
- Test matching logic (direct match, parent directory prefix, import-based match)
- Flagging conditions (untested source, net test reduction, source without test effort)
- Output format (markdown table, inline comments, activity log)
- Early exit conditions (test-only PR, docs-only PR, no significant source changes)

**Model**: `claude-haiku-4-5` (fast categorization)
**Marker**: `<!-- test-coverage-review -->` (ensures one summary comment per PR, updates replace previous)

## Integration with 5-Layer Test Architecture

The agent's "legitimately untestable" categorization aligns with erk's test layers:

- **Legitimately untestable**: Layers 0-2 (CLI wrappers, type definitions, ABCs)
- **Requires tests**: Layers 3-4 (business logic, operations)

See [Testing Reference](../testing/testing.md) for the full test architecture.

## Related Documentation

- [Convention-Based Reviews](../ci/convention-based-reviews.md) - Review discovery and execution system
- [Testing Tripwires](../testing/tripwires.md) - Test-related constraints
