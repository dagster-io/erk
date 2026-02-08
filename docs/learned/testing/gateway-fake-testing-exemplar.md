---
title: Gateway Fake Testing Exemplar
read_when:
  - "writing tests for gateway fakes that return discriminated unions"
  - "deciding whether mutation tracking should occur on error paths"
  - "implementing a new fake gateway method with error injection"
tripwires:
  - action: "creating a fake gateway without constructor-injected error configuration"
    warning: "Fakes must accept error variants at construction time (e.g., push_to_remote_error=PushError(...)) to enable failure injection in tests."
  - action: "using truthiness checks or .success on discriminated union results in tests"
    warning: "Always use isinstance() for type narrowing. Never check bool(result) or result.success — these bypass the type system."
  - action: "tracking mutations before checking error configuration in a fake method"
    warning: "Decide deliberately: should this operation track even on failure? push_to_remote skips tracking on error (nothing happened), pull_rebase always tracks (the attempt matters). Match the real operation's semantics."
---

# Gateway Fake Testing Exemplar

This document captures the cross-cutting design decisions in fake gateway testing — specifically, the three patterns that every fake test must exercise and the subtle tracking-on-error decision that differs between operations.

## Why Fakes Need Their Own Tests

Fakes are production code for tests. A broken fake silently produces false-positive test results across the entire test suite. The `tests/unit/fakes/` directory exists to verify that fakes honor their ABC contracts and that their error-injection and mutation-tracking machinery works correctly.

<!-- Source: tests/unit/fakes/test_fake_git_remote_ops.py -->

See `test_fake_git_remote_ops.py` in `tests/unit/fakes/` for the canonical exemplar.

## Three Required Test Categories Per Operation

Every fake method that returns a discriminated union needs three test categories:

| Category | What it verifies | Why it matters |
|---|---|---|
| **Default success** | No-arg construction returns success variant | Proves fakes are zero-configuration for happy paths |
| **Error injection** | Constructor-configured error is returned | Proves failure paths work without modifying fake internals |
| **Mutation tracking** | Operations record calls via read-only properties | Proves test assertions can verify what operations occurred |

Organize tests by operation (one test class per ABC method), not by category. Each class covers all three categories for its operation.

## The Tracking-on-Error Decision

The most subtle design choice in fake implementation is whether mutation tracking should occur when an error is configured. This is not arbitrary — it follows the real operation's semantics:

| Operation | Tracks on error? | Rationale |
|---|---|---|
| `push_to_remote` | No | A rejected push didn't actually push anything — tracking it would misrepresent what happened |
| `pull_rebase` | Yes | The rebase was attempted (and may have partially applied) — the attempt itself is meaningful for test assertions |

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/remote_ops/fake.py, FakeGitRemoteOps.push_to_remote -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/remote_ops/fake.py, FakeGitRemoteOps.pull_rebase -->

Compare `FakeGitRemoteOps.push_to_remote()` (early-returns error before tracking) with `FakeGitRemoteOps.pull_rebase()` (tracks first, then checks error) in `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/fake.py`.

**When implementing a new fake method**, ask: "If the real operation fails, did a side effect still occur?" If yes, track before checking the error. If no, check the error first and skip tracking.

## Mutation Tracking via link_mutation_tracking

When a sub-gateway fake (like `FakeGitRemoteOps`) is composed inside a parent fake (like `FakeGit`), mutation lists must be shared so that assertions on the parent see mutations from the sub-gateway.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/remote_ops/fake.py, FakeGitRemoteOps.link_mutation_tracking -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/fake.py, FakeGit.__init__ -->

See `FakeGitRemoteOps.link_mutation_tracking()` and how `FakeGit.__init__()` calls it in `packages/erk-shared/src/erk_shared/gateway/git/fake.py`.

The mechanism: the parent creates the mutable tracking lists in its own `__init__`, then passes those same list objects to the sub-gateway's `link_mutation_tracking()`, which replaces the sub-gateway's internal lists. Both parent and sub-gateway now append to the same list.

This is why sub-gateway fakes work both standalone (in fake-specific tests) and composed (in business logic tests via `FakeGit`).

## Anti-Patterns

**Using truthiness or `.success` on union results:**

```python
# WRONG — bypasses type system, breaks on empty success markers
if result:
    ...
if result.success:
    ...

# RIGHT — isinstance() enables type narrowing
if isinstance(result, PushError):
    ...
```

**Testing only the happy path:** Every discriminated union method needs both success and error tests. A fake that only tests success could silently break error injection for all consumers.

## Related Documentation

- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) — The 5-place implementation pattern that fakes are part of
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — Design decisions for when to use unions vs exceptions
