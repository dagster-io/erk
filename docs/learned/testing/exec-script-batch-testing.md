---
title: Exec Script Batch Testing
read_when:
  - writing tests for batch exec commands
  - organizing test cases for JSON stdin/stdout commands
  - adding failure injection to a fake gateway for batch operations
tripwires:
  - action: "Test only success cases for batch commands"
    warning: "Cover all four categories: success, partial failure, validation errors, and JSON structure. Missing any category leaves a critical gap."
    score: 7
  - action: "Use stateful failure injection (_should_fail_next flags) in fake gateways"
    warning: "Use set-based constructor injection instead. Stateful flags are order-dependent and brittle. See the set-based pattern below."
    score: 6
last_audited: "2026-02-08"
audit_result: edited
---

# Exec Script Batch Testing

Batch exec commands have a unique testing challenge: they process multiple items in one invocation, so a single happy-path test leaves most failure modes uncovered. This document captures the four-category test organization and the set-based failure injection pattern that makes partial failure testing declarative.

## Why Four Categories

A batch command can fail in structurally different ways, and each failure shape produces different JSON output. Testing only success cases misses the three other shapes entirely:

| Category             | What it proves                                            | Output shape                    |
| -------------------- | --------------------------------------------------------- | ------------------------------- |
| **Success**          | All items processed correctly, AND semantics hold         | `{success: true, results: []}`  |
| **Partial failure**  | Failed items don't block successful ones, per-item errors | `{success: false, results: []}` |
| **Input validation** | Malformed input rejected before any side effects          | `{success: false, error_type}`  |
| **JSON structure**   | Field presence and types match the contract               | Both shapes                     |

The critical distinction is between partial failure (results array present, some items failed) and validation failure (no results array, nothing processed). These are different JSON shapes and callers branch on the presence of `results` — if you only test success, you never verify either failure shape.

### Success cases to cover

- Empty batch — proves the command handles zero items gracefully
- Single item — the degenerate case, catches off-by-one errors
- Multiple items (2-3) — proves iteration works
- Optional fields present/absent — e.g., explicit `null` vs omitted field, catches coercion bugs

### Partial failure: the side-effect check

The most important assertion in partial failure tests: **verify that successful items were still processed** even though others failed. Check the fake gateway's mutation tracking properties to confirm side effects occurred for successful items and did not occur for failed items.

### Input validation: the atomicity check

The most important assertion: **verify zero side effects when validation fails**. After sending malformed input, assert that the fake gateway's mutation tracking is empty. This proves the two-phase (validate-then-process) contract holds.

## Set-Based Failure Injection

To test partial failures, fake gateways accept a set of identifiers that should fail. The fake checks membership at call time and returns a failure result for matching identifiers.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/fake.py, FakeGitHub.__init__ resolve_thread_failures parameter -->

See the `resolve_thread_failures` parameter on `FakeGitHub.__init__()` in `packages/erk-shared/src/erk_shared/gateway/github/fake.py`. The same pattern appears for other failure modes across fakes (e.g., `tracking_branch_failures` on `FakeGitBranchOps`).

### Why set-based over stateful

Set-based injection is **declarative**: the test declares _which_ identifiers fail, not _when_ they fail. This matters because batch processing order is an implementation detail — if the command reorders items internally, set-based tests still work.

**Anti-pattern: Stateful injection**

```python
# WRONG: Order-dependent, breaks if processing order changes
fake.fail_next_call()  # Which call? Depends on iteration order
fake._should_fail_next = True  # Unclear which item triggers this
```

Stateful flags couple tests to processing order, create ambiguity about which item fails, and require careful reset between test cases. Set-based injection has none of these problems — you declare the failure set once in the constructor and the fake handles the rest.

### Extending the pattern to new batch commands

When adding failure injection for a new operation:

1. Add a constructor parameter to the fake: `{operation}_failures: set[str] | None`
2. Store it as `self._{operation}_failures`
3. In the method, check `if identifier in self._{operation}_failures: return failure_result`
4. The parameter type should match the identifier type used in the batch input (usually `str`)

This follows the existing convention — `FakeGitHub` uses `resolve_thread_failures: set[str]`, `FakeGitBranchOps` uses `tracking_branch_failures: dict[str, str]` (dict when failure needs an error message, set when a boolean is sufficient).

## Test File Organization

<!-- Source: tests/unit/cli/commands/exec/scripts/test_resolve_review_threads.py -->

Batch tests use section comment headers (`# === Success Cases ===`) to visually group the four categories within a single file. See `test_resolve_review_threads.py` for the reference structure.

Tests invoke commands through `CliRunner.invoke()` with `ErkContext.for_test()` for dependency injection. Never use `monkeypatch` or custom test helpers — the fake gateway + `ErkContext.for_test()` pattern provides all the control you need. Assert side effects via the fake's read-only tracking properties (e.g., `resolved_thread_ids`, `thread_replies`).

## Related Documentation

- [batch-exec-commands.md](../cli/batch-exec-commands.md) — Batch command design contract (five-step contract, success semantics, two response shapes)
- [testing.md](testing.md) — General erk testing patterns
- [exec-script-schema-patterns.md](../cli/exec-script-schema-patterns.md) — TypedDict vs dataclass decisions for batch I/O
