---
title: Makefile Testing Targets for erkdesk
category: cli
read_when:
  - running erkdesk tests locally or in CI
  - adding new test commands to the Makefile
  - understanding erkdesk CI integration
---

# Makefile Testing Targets for erkdesk

The erk Makefile includes targets for running erkdesk tests alongside Python tests, following the established `{package}-test` naming convention.

## Available Targets

### erkdesk-test

Single test run for CI.

```bash
make erkdesk-test
```

**Equivalent pnpm command:**

```bash
cd erkdesk && pnpm test
```

**Use cases:**

- CI pipelines
- Pre-commit verification
- Final validation before PR submission

**Behavior:**

- Runs all tests once
- Exits with non-zero status on failure
- No watch mode

### erkdesk-test-watch

Watch mode for local development.

```bash
make erkdesk-test-watch
```

**Equivalent pnpm command:**

```bash
cd erkdesk && pnpm run test:watch
```

**Use cases:**

- Active development
- TDD workflow
- Debugging test failures

**Behavior:**

- Watches files for changes
- Re-runs affected tests automatically
- Interactive mode (press keys to filter/re-run)

## CI Integration

### fast-ci Target

The `make fast-ci` target includes erkdesk tests alongside Python unit tests:

```bash
make fast-ci
```

**Total tests run:**

- Python unit tests: ~4700+
- Erkdesk component tests: ~10+
- **Combined: 4712+**

**Run time:** ~30 seconds (as of 2025-01)

### all-ci Target

The `make all-ci` target runs the full test suite including integration tests:

```bash
make all-ci
```

**Includes:**

- All `fast-ci` tests (Python unit + erkdesk)
- Python integration tests
- End-to-end tests

**Run time:** ~2-3 minutes (as of 2025-01)

## Naming Convention

Erkdesk targets follow the established pattern for package-specific test commands:

| Package      | Test Target         | Watch Target              |
| ------------ | ------------------- | ------------------------- |
| Python (erk) | `make test`         | `make test-watch`         |
| Erkdesk      | `make erkdesk-test` | `make erkdesk-test-watch` |

**Rationale:**

- Consistent with existing Makefile patterns
- Easy to remember: `{package}-test` + optional `-watch` suffix
- Namespaced to avoid conflicts with top-level `test` target

## Direct pnpm Commands

You can also run tests directly with pnpm from the erkdesk directory:

```bash
# From erk root
cd erkdesk

# Single run
pnpm test

# Watch mode
pnpm run test:watch

# With coverage
pnpm run test:coverage
```

**Why use Makefile targets instead?**

- Works from any directory (don't need to `cd erkdesk`)
- Consistent with Python test workflow
- CI scripts use Makefile targets

## Adding New Test Targets

When adding new test-related Makefile targets for erkdesk:

1. **Name it `erkdesk-{action}`** - maintain the package prefix
2. **Add both single-run and watch variants** - if applicable
3. **Document the equivalent pnpm command** - for users who prefer direct pnpm
4. **Update this doc** - keep the reference current

Example:

```makefile
.PHONY: erkdesk-test-coverage
erkdesk-test-coverage:
	cd erkdesk && pnpm run test:coverage

.PHONY: erkdesk-test-coverage-watch
erkdesk-test-coverage-watch:
	cd erkdesk && pnpm run test:coverage -- --watch
```

## Debugging Test Failures

### Run specific test file

```bash
# Via Makefile (from root)
cd erkdesk && pnpm test -- PlanList.test.tsx

# Via pnpm (from erkdesk/)
pnpm test -- PlanList.test.tsx
```

### Run with verbose output

```bash
cd erkdesk && pnpm test -- --reporter=verbose
```

### Run in UI mode

```bash
cd erkdesk && pnpm exec vitest --ui
```

Opens browser-based test UI for interactive debugging.

## Related

- [Vitest Configuration](../desktop-dash/vitest-setup.md) - Test runner setup
- [Erkdesk Component Testing Patterns](../testing/erkdesk-component-testing.md) - Writing tests
