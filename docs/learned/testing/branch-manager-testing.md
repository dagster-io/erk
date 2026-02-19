---
title: Branch Manager Testing Patterns
read_when:
  - "writing tests that involve branch creation or Graphite tracking"
  - "injecting FakeBranchManager or FakeGraphite in tests"
  - "debugging checkout count assertion failures in branch-related tests"
tripwires:
  - action: "injecting FakeBranchManager directly in tests"
    warning: "BranchManager is a lazy property on ErkContext. Inject FakeGraphite via context_for_test(graphite=fake_graphite) instead."
last_audited: "2026-02-19 00:00 PT"
audit_result: clean
---

# Branch Manager Testing Patterns

BranchManager is a lazy property on `ErkContext` (constructed from `context.py`), not a separately injectable gateway. This means you cannot inject a `FakeBranchManager` directly — instead, you inject the underlying `FakeGraphite` and let the context build the real `BranchManager` from it.

## Injection Pattern

Inject `FakeGraphite` via `context_for_test(graphite=fake_graphite)`. The context constructs a `GraphiteBranchManager` internally using the provided `FakeGraphite`, mirroring production behavior where `BranchManager` is built from the real `Graphite` gateway.

<!-- Source: tests/unit/cli/commands/exec/scripts/test_plan_save.py, test_draft_pr_tracks_branch_with_graphite -->

See `test_draft_pr_tracks_branch_with_graphite()` in `tests/unit/cli/commands/exec/scripts/test_plan_save.py:278-288` for the injection pattern.

## Verifying Branch Tracking

`FakeGraphite` exposes `track_branch_calls` for asserting that Graphite tracking was invoked. Each entry is a tuple of `(repo_root, branch_name, parent_branch)`. `FakeGraphite.create_linked_branch_ops()` creates ops with shared mutation tracking, so all assertions go through the single `FakeGraphite` instance.

<!-- Source: tests/unit/cli/commands/exec/scripts/test_plan_save.py, test_draft_pr_tracks_branch_with_graphite -->

See `test_draft_pr_tracks_branch_with_graphite()` in `tests/unit/cli/commands/exec/scripts/test_plan_save.py:278-303` for the complete assertion example.

## Checkout Count Expectations

When converting from `git.branch.create_branch()` to `branch_manager.create_branch()`, expect additional checkouts from BranchManager's internal `gt track` sequence:

- `branch_manager.create_branch()` performs **2 internal checkouts**: checkout new branch for `gt track`, then restore original branch
- Your code's own checkout/restore adds more

For example, `plan_save` does:

1. `branch_manager.create_branch()` → 2 checkouts (new branch + restore)
2. Plan save's own checkout of plan branch → 1 checkout
3. Plan save's restore of original branch → 1 checkout
4. **Total: 4 checkouts**

The sequence is: gt track checkout → gt track restore → plan commit checkout → plan commit restore (4 total).

<!-- Source: tests/unit/cli/commands/exec/scripts/test_plan_save.py, test_draft_pr_restores_original_branch -->

See `test_draft_pr_restores_original_branch()` in `tests/unit/cli/commands/exec/scripts/test_plan_save.py:220-236` for the checkout count assertions.

## Related Topics

- [Branch Manager Decision Tree](../architecture/branch-manager-decision-tree.md) - When to use `ctx.branch_manager` vs `ctx.git.branch`
- [Branch Manager Abstraction](../architecture/branch-manager-abstraction.md) - Architecture and behavioral differences
- [Frozen Dataclass Test Doubles](frozen-dataclass-test-doubles.md) - General testing pattern for gateway fakes
