---
title: Makefile Testing Targets for erkdesk
category: cli
read_when:
  - running erkdesk tests locally or in CI
  - adding new test commands to the Makefile
  - understanding erkdesk CI integration
---

# Makefile Testing Targets for erkdesk

## Why Makefile Targets for TypeScript Tests

The erk project runs TypeScript (erkdesk) and Python tests through the same Makefile interface to provide **location-independent execution**. Developers can run `make erkdesk-test` from any directory in the monorepo without remembering to `cd erkdesk` first.

This design choice prioritizes consistency over directness: CI scripts, developer workflows, and documentation all reference the same `make` targets, avoiding the "works on my machine" problem caused by different working directory assumptions.

## Naming Convention: Package-Prefixed Targets

<!-- Source: Makefile, erkdesk-* target definitions -->

All erkdesk targets follow the `{package}-{action}` pattern to avoid namespace collisions with top-level test commands. The pattern mirrors existing Python package test targets like `test-erk-dev`.

See erkdesk target definitions in `Makefile`.

| Target Pattern         | Purpose                          | Example              |
| ---------------------- | -------------------------------- | -------------------- |
| `{package}-{action}`   | Single-run command for CI        | `erkdesk-test`       |
| `{package}-{action}-*` | Variants with additional options | `erkdesk-test-watch` |

**Why not top-level `test-erkdesk`?** The package name goes first to group all erkdesk-related targets alphabetically in tab completion and `make -p` output.

## Fast-CI Integration

<!-- Source: Makefile, fast-ci target -->

The `fast-ci` target includes erkdesk tests alongside Python unit tests, creating a **single unified CI feedback loop**. This was a deliberate architectural decision: erkdesk is not a separate project—it's part of the erk monorepo and must pass the same quality gate.

See the `fast-ci` target composition in `Makefile`.

The combined test count (Python unit + erkdesk component) continues to grow. The combined run time stays under 30 seconds because:

1. Python tests use `pytest -n auto` for parallelization
2. Vitest runs erkdesk tests in parallel by default
3. Both test suites avoid I/O and subprocess calls (unit test discipline)

**Why erkdesk in fast-ci but not all-ci?** Because `all-ci` already includes everything in `fast-ci`. The distinction is unit-only (fast) vs unit+integration (all).

## Watch Mode: Development vs CI Split

<!-- Source: Makefile, erkdesk-test vs erkdesk-test-watch -->
<!-- Source: erkdesk/package.json, test vs test:watch scripts -->

The Makefile exposes two test modes that map to different pnpm scripts:

See watch mode implementation in `Makefile` and `erkdesk/package.json`.

| Makefile Target      | pnpm Script  | Exit Behavior           | Interactive |
| -------------------- | ------------ | ----------------------- | ----------- |
| `erkdesk-test`       | `pnpm test`  | Non-zero on failure     | No          |
| `erkdesk-test-watch` | `test:watch` | Stays running on change | Yes         |

**CI uses single-run mode** (`erkdesk-test`) because GitHub Actions workflows need deterministic exit codes. Watch mode would hang the CI runner indefinitely.

**Local TDD uses watch mode** to minimize feedback latency. Vitest's watch mode only re-runs affected tests when files change, avoiding the full test suite penalty.

## Anti-Pattern: Don't Add Coverage Targets Without Audit

The Makefile intentionally omits `erkdesk-test-coverage` targets despite package.json supporting them. Coverage tracking adds 20-30% overhead to test runs and wasn't justified when erkdesk had 10 tests.

**Before adding coverage targets:**

1. Ensure erkdesk has >100 tests (otherwise coverage is just overhead noise)
2. Integrate coverage into CI gating (not just local runs)
3. Set minimum thresholds in vitest config (don't rely on manual enforcement)

**When to add:** After erkdesk component count exceeds 20 and test suite justifies coverage tracking.

## Decision Tree: When to Use Which Command

```
Need to run tests?
├─ Are you in active development?
│  └─ YES → make erkdesk-test-watch (or cd erkdesk && pnpm run test:watch)
│
├─ Are you verifying before a commit?
│  └─ YES → make fast-ci (tests erkdesk + Python together)
│
├─ Are you debugging a specific test file?
│  └─ YES → cd erkdesk && pnpm test -- FileName.test.tsx
│
└─ Are you running CI locally?
   └─ YES → make all-ci (full validation)
```

**Rationale for recommending fast-ci over erkdesk-test:** Individual package tests don't catch cross-boundary issues. Running the unified fast-ci target prevents "Python tests passed but I broke the Python→TypeScript bridge" failures.

## Extending the Pattern: Future Package Tests

When adding new testable packages (e.g., a future `erkweb` component):

1. **Add `{package}-test` and `{package}-test-watch` targets** to Makefile
2. **Integrate into `fast-ci`** if tests are fast (<30s contribution)
3. **Document here** so the pattern remains discoverable

<!-- Source: Makefile, .PHONY declarations -->

The `.PHONY` declaration lists all non-file targets. Add new erkdesk targets there to prevent Makefile from treating them as file paths.

## See Also

- [Vitest Configuration](../desktop-dash/vitest-setup.md) — Test runner setup for erkdesk
- [Erkdesk Component Testing Patterns](../testing/erkdesk-component-testing.md) — Writing tests that match CI expectations
