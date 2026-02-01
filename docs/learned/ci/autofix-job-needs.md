---
title: Autofix Job Needs
read_when:
  - "modifying the autofix job's needs list in ci.yml"
  - "adding a new CI job that might block autofix"
  - "understanding why autofix is blocked on test failures"
tripwires:
  - action: "adding a new CI job to the autofix job's needs list"
    warning: "Only add jobs whose failures can be auto-fixed (format, lint, prettier). Test jobs (erkdesk-tests, unit-tests, integration-tests) should NOT block autofix. Adding them causes the entire pipeline to block on test failures that autofix cannot resolve."
---

# Autofix Job Needs

The `autofix` job in `.github/workflows/ci.yml` automatically fixes formatting and linting issues. Its `needs` list determines which jobs must complete before autofix runs.

## Design Principle: Only Block on Fixable Failures

The autofix job should **only** depend on jobs whose failures it can fix:

- **Format checks** (ruff format, prettier) → Fixable
- **Lint checks** (ruff check) → Fixable
- **Type checks** (ty check) → NOT fixable (but runs fast, included for early feedback)

Test jobs should **NOT** block autofix:

- **erkdesk-tests** → NOT fixable
- **unit-tests** → NOT fixable
- **integration-tests** → NOT fixable

## Why This Matters

If autofix depends on test jobs, the entire pipeline blocks when tests fail:

1. Test fails (e.g., erkdesk-tests)
2. Autofix waits for test completion (it's in the needs list)
3. Autofix never runs because the test failed
4. Format/lint issues never get fixed
5. Developer must manually fix tests AND format/lint issues

**Correct behavior**: Autofix runs independently, fixes format/lint issues, then tests run against the fixed code.

## Current Needs List

From `.github/workflows/ci.yml`:

```yaml
autofix:
  needs: [ty, format, lint, prettier]
  # Notably EXCLUDES: erkdesk-tests, unit-tests, integration-tests
```

## When to Add a Job to Needs

**Add to needs** if:

- The job checks something autofix can fix (formatting, linting)
- Autofix needs the job's output to know what to fix

**Do NOT add to needs** if:

- The job runs tests (unit, integration, component)
- The job checks correctness (not style/format)
- Failures require manual code changes (not auto-fixable)

## Example: erkdesk-tests

When erkdesk tests were added (PR #6501), they were correctly **excluded** from the autofix needs list:

**Correct**:

```yaml
autofix:
  needs: [ty, format, lint, prettier] # erkdesk-tests NOT included
```

**Wrong**:

```yaml
autofix:
  needs: [ty, format, lint, prettier, erkdesk-tests] # BLOCKS on test failures!
```

## Related Patterns

- [CI Iteration Pattern](ci-iteration.md) - How to handle CI failures iteratively
- [Workflow Gating Patterns](workflow-gating-patterns.md) - Conditional job execution
