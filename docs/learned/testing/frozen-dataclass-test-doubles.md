---
title: Frozen Dataclass Test Doubles
read_when:
  - "implementing a fake for an ABC interface"
  - "adding mutation tracking to a test double"
  - "choosing between frozen dataclass fakes and __init__-based fakes"
  - "writing tests that assert on method call parameters"
tripwires:
  - action: "exposing a mutation tracking list directly as a property without copying"
    warning: "Return list(self._tracked_list) from properties, not self._tracked_list. Direct exposure lets test code accidentally mutate the tracking state."
  - action: "tracking only the primary argument in a mutation tuple, omitting flags or options"
    warning: "Track ALL call parameters in tuples (e.g., (branch, force) not just branch). Lost context leads to undertested behavior."
  - action: "creating a fake that uses __init__ when frozen dataclass would work"
    warning: "FakeBranchManager uses frozen dataclass because its state is simple and declarative. FakeGitHub uses __init__ because it has 30+ constructor params. Choose based on complexity."
last_audited: "2026-02-08"
audit_result: edited
---

# Frozen Dataclass Test Doubles

Erk's gateway fakes use two distinct patterns for mutation tracking: frozen dataclasses with mutable internals (for simpler fakes) and `__init__`-based classes (for complex fakes). Both patterns serve the same purpose — recording method calls so tests can assert on what happened — but the choice between them has architectural consequences.

## Why Two Patterns Exist

The codebase uses frozen dataclass fakes and `__init__`-based fakes for different situations. The split isn't arbitrary — it reflects a complexity threshold.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/branch_manager/fake.py, FakeBranchManager -->

`FakeBranchManager` uses `@dataclass(frozen=True)` because it has a manageable number of fields (around 15), all with `field(default_factory=...)` defaults. The frozen constraint provides a useful guarantee: field references can't be reassigned after construction, so a mutation tracking list can't be accidentally replaced.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/fake.py, FakeGitHub -->

`FakeGitHub` uses a plain `__init__` because it has 30+ constructor parameters covering PRs, workflows, issues, reviews, diffs, labels, gists, and commit statuses. Making this frozen would gain little — the class is already too complex for the frozen constraint to meaningfully protect against misuse. The `__init__` approach also allows mutation tracking lists to be initialized imperatively alongside the pre-configured state.

| Criterion | Frozen Dataclass | `__init__`-based |
| --- | --- | --- |
| Constructor complexity | < ~15 fields | 15+ fields |
| State initialization | Declarative (`field(default_factory=...)`) | Imperative (assignment in `__init__`) |
| Field reassignment protection | Yes (`FrozenInstanceError`) | No |
| Erk examples | `FakeBranchManager` | `FakeGitHub`, `FakeGitBranchOps` |

## The Mutable-Internals Trick

Frozen dataclasses prevent field *reassignment*, but they don't prevent mutation of the *contents* of mutable fields. A `list` field in a frozen dataclass can still be appended to — only the reference to the list is frozen, not the list itself. This is standard Python reference semantics, not a hack.

This means frozen fakes can track mutations by appending to internal lists while still preventing accidental field replacement. A test can't do `fake._deleted_branches = []` (raises `FrozenInstanceError`), but the fake's own methods can do `self._deleted_branches.append(...)`.

## The Copy-on-Read Property Pattern

Both fake variants expose mutation tracking via properties that return **copies** of internal lists. This prevents test code from accidentally modifying the tracking state through the returned reference.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/branch_manager/fake.py, FakeBranchManager.deleted_branches -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/fake.py, FakeGitBranchOps.deleted_branches -->

See `FakeBranchManager.deleted_branches` and `FakeGitBranchOps.deleted_branches` for the canonical pattern — both return `list(self._internal_list)`.

**Anti-pattern — direct exposure:**

```python
# WRONG: Returns the actual tracking list, not a copy
@property
def deleted_branches(self) -> list[str]:
    return self._deleted_branches  # Test code can .clear() this!
```

## Track All Parameters, Not Just Primary Keys

Mutation tuples should capture the full call context — every parameter that affects behavior. Tracking only the primary argument (e.g., branch name) discards information that tests need to verify.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/branch_manager/fake.py, FakeBranchManager -->

`FakeBranchManager` demonstrates this consistently: `_deleted_branches` tracks `(branch, force)`, `_created_branches` tracks `(branch_name, base_branch)`, `_created_tracking_branches` tracks `(branch, remote_ref)`. The `force` flag on deletion and the `base_branch` on creation are both behaviors that callers care about testing.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/fake.py, FakeGitHub -->

`FakeGitHub` takes this further with `_created_prs` tracking 5-tuples of `(branch, title, body, base, draft)` and `_created_commit_statuses` tracking 5-tuples of `(repo, sha, state, context, description)`.

## Linked Mutation Tracking Across Fakes

When a higher-level fake (like `FakeBranchManager`) delegates to a lower-level fake (like `FakeGitBranchOps`), mutations need to be visible through both interfaces. Without linking, tests that check `FakeGit.deleted_branches` won't see deletions that went through `BranchManager`.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/fake.py, FakeGitBranchOps.link_mutation_tracking -->

`FakeGitBranchOps.link_mutation_tracking()` solves this by replacing its internal tracking lists with references to the parent fake's lists. After linking, mutations through either path are recorded in the same lists. This is why `FakeGitBranchOps` uses `__init__` instead of frozen dataclass — the linking method needs to reassign `self._created_branches` and other fields, which `frozen=True` would prevent.

## Related Documentation

- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) — the 5-file pattern that fakes implement, including the fake mutation tracking checklist
- [BranchManager Abstraction](../architecture/branch-manager-abstraction.md) — the dual-mode abstraction that motivates the frozen dataclass fake variant
