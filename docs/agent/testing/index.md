---
title: Testing Documentation
read_when:
  - "writing tests"
  - "using erk fakes"
  - "fixing test infrastructure conflicts"
---

# Testing Documentation

**First**: Load the `fake-driven-testing` skill for testing philosophy, 5-layer strategy, and patterns.

This category contains erk-specific test reference material.

## Quick Navigation

| When you need to...              | Do this                                            |
| -------------------------------- | -------------------------------------------------- |
| Understand testing philosophy    | Load `fake-driven-testing` skill                   |
| Use erk fakes (FakeGit, etc.)    | [testing.md](testing.md)                           |
| Run erk test commands            | [testing.md](testing.md)                           |
| Fix rebase conflicts in tests    | [rebase-conflicts.md](rebase-conflicts.md)         |
| Create session log test fixtures | [session-log-fixtures.md](session-log-fixtures.md) |

## Documents in This Category

### Erk Test Reference

**File:** [testing.md](testing.md)

Erk-specific fakes (FakeGit, FakeConfigStore, etc.), test helpers (erk_isolated_fs_env, create_test_context), and make targets.

### Session Log Test Fixtures

**File:** [session-log-fixtures.md](session-log-fixtures.md)

Creating realistic JSONL test fixtures for session-scoped features: fixture patterns, organization, minimal examples, and common mistakes to avoid.

### Rebase Test Conflicts

**File:** [rebase-conflicts.md](rebase-conflicts.md)

Resolving erk-specific test conflicts during rebases: ErkContext API evolution, env_helpers patterns, parameter renames.

## Related

- **Testing philosophy**: Load `fake-driven-testing` skill
- [Architecture](../architecture/) - Patterns that enable testable code
