---
title: Autofix Job Needs
read_when:
  - "modifying the autofix job's needs list in ci.yml"
  - "adding a new CI job that might block autofix"
  - "understanding why autofix runs independently of tests"
tripwires:
  - action: "adding a test job to autofix's needs list"
    warning: "Test jobs (erkdesk-tests, unit-tests, integration-tests) must NEVER block autofix. Only jobs whose failures can be auto-resolved (format, lint, prettier, docs-check, ty) should be dependencies. Adding test jobs creates a deadlock: tests fail → autofix blocked → format/lint issues never fixed → developer must manually fix both."
---

# Autofix Job Needs

## The Core Constraint

The autofix job exists to fix style/format issues automatically. Its dependency list determines whether it can fulfill this purpose or becomes blocked.

**Design principle**: Only depend on jobs whose failures autofix can resolve.

<!-- Source: .github/workflows/ci.yml, autofix job needs array -->

See the `autofix` job's `needs` array in `.github/workflows/ci.yml`.

## Why This Design Matters

When autofix depends on test jobs, the pipeline enters a deadlock state:

1. Test fails (e.g., broken unit test)
2. Autofix waits for test completion (declared dependency)
3. Test job fails → autofix never runs
4. Format/lint violations remain unfixed
5. Developer must manually fix both test AND style issues

**The insight**: Style violations are orthogonal to correctness failures. Autofix should fix style violations regardless of test state, then tests run against the cleaned-up code.

## Decision Table: When to Add Dependencies

| Job Type             | Failures Auto-Fixable? | Add to needs? | Rationale                                                                            |
| -------------------- | ---------------------- | ------------- | ------------------------------------------------------------------------------------ |
| format (ruff format) | ✅ Yes                 | ✅ Yes        | Autofix runs ruff format to resolve                                                  |
| lint (ruff check)    | ✅ Yes                 | ✅ Yes        | Autofix runs ruff check --fix                                                        |
| prettier             | ✅ Yes                 | ✅ Yes        | Autofix runs prettier --write                                                        |
| docs-check           | ✅ Yes                 | ✅ Yes        | Autofix runs make docs-sync                                                          |
| ty (type check)      | ⚠️ Mostly no           | ✅ Yes        | Fast feedback; most type errors need manual fixes but some are auto-fixable via ruff |
| unit-tests           | ❌ No                  | ❌ **NO**     | Requires code changes, not style fixes                                               |
| integration-tests    | ❌ No                  | ❌ **NO**     | Requires code changes, not style fixes                                               |
| erkdesk-tests        | ❌ No                  | ❌ **NO**     | Requires code changes, not style fixes                                               |

## Anti-Pattern: Test Job Dependency

**WRONG** - This blocks autofix on test failures:

```yaml
autofix:
  needs: [format, lint, prettier, docs-check, ty, unit-tests]
  # ❌ unit-tests will prevent autofix from running when tests fail
```

**Correct** - Autofix runs independently:

<!-- Source: .github/workflows/ci.yml, autofix job needs array -->

The actual configuration excludes all test jobs from the needs list.

## Historical Context

When erkdesk-tests were added (PR #6501), the temptation was to add them to the autofix needs list "for consistency" since other jobs were listed. This would have been incorrect — erkdesk tests verify JavaScript correctness, which autofix cannot repair.

The pattern was correctly maintained: only fixable jobs in the dependency list.

## Related Patterns

- [CI Iteration Pattern](ci-iteration.md) - Iterative fixing of CI failures
- [Workflow Gating Patterns](workflow-gating-patterns.md) - Conditional job execution strategies
