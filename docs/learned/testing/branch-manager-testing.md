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

Inject `FakeGraphite` via `context_for_test()`:

```python
from tests.fakes import FakeGraphite, context_for_test

fake_graphite = FakeGraphite()
ctx = context_for_test(
    graphite=fake_graphite,
    # ... other fakes
)
```

The context constructs a `GraphiteBranchManager` internally using the provided `FakeGraphite`. This mirrors production behavior where `BranchManager` is built from the real `Graphite` gateway.

## Verifying Branch Tracking

`FakeGraphite` exposes `track_branch_calls` for asserting that Graphite tracking was invoked:

```python
assert len(fake_graphite.track_branch_calls) == 1
tracked_call = fake_graphite.track_branch_calls[0]
assert tracked_call[0] == tmp_path      # repo_root
assert tracked_call[1] == branch_name   # branch_name
assert tracked_call[2] == "main"        # parent_branch
```

`FakeGraphite.create_linked_branch_ops()` creates ops with shared mutation tracking, so all assertions go through the single `FakeGraphite` instance.

<!-- Source: tests/unit/cli/commands/exec/scripts/test_plan_save.py, test_draft_pr_tracks_branch_with_graphite -->

See `test_draft_pr_tracks_branch_with_graphite()` in `tests/unit/cli/commands/exec/scripts/test_plan_save.py:278-303` for a complete example.

## Checkout Count Expectations

When converting from `git.branch.create_branch()` to `branch_manager.create_branch()`, expect additional checkouts from BranchManager's internal `gt track` sequence:

- `branch_manager.create_branch()` performs **2 internal checkouts**: checkout new branch for `gt track`, then restore original branch
- Your code's own checkout/restore adds more

For example, `plan_save` does:

1. `branch_manager.create_branch()` → 2 checkouts (new branch + restore)
2. Plan save's own checkout of plan branch → 1 checkout
3. Plan save's restore of original branch → 1 checkout
4. **Total: 4 checkouts**

```python
# Four checkouts: branch_manager.create_branch() does checkout+restore for gt track,
# then plan_save does checkout+restore for committing plan file
assert len(fake_git.checked_out_branches) == 4
assert fake_git.checked_out_branches[0][1].startswith("plan-")    # for gt track
assert fake_git.checked_out_branches[1] == (tmp_path, "feature-branch")  # restore
assert fake_git.checked_out_branches[2][1].startswith("plan-")    # for plan commit
assert fake_git.checked_out_branches[3] == (tmp_path, "feature-branch")  # final restore
```

<!-- Source: tests/unit/cli/commands/exec/scripts/test_plan_save.py, test_draft_pr_restores_original_branch -->

See `test_draft_pr_restores_original_branch()` in `tests/unit/cli/commands/exec/scripts/test_plan_save.py:220-236` for the full example.

## Related Topics

- [Branch Manager Decision Tree](../architecture/branch-manager-decision-tree.md) - When to use `ctx.branch_manager` vs `ctx.git.branch`
- [Branch Manager Abstraction](../architecture/branch-manager-abstraction.md) - Architecture and behavioral differences
- [Frozen Dataclass Test Doubles](frozen-dataclass-test-doubles.md) - General testing pattern for gateway fakes
