# Plan: Remove Legacy FakeGitHubGtKitOps and Unify on FakeGitHub

## Goal

Complete the consolidation of GitHub operations by removing legacy duplicate fake implementations and making `FakeGtKitOps` use the unified `FakeGitHub` from `erk_shared.github.fake`.

## Background

The original plan to "Merge GitHubGtKit into GitHub(ABC)" is **95% already implemented**:

- GitHub(ABC) has all 32+ methods including GT-kit methods
- GtKit.github() already returns `GitHub` (not a separate GitHubGtKit)
- FakeGitHub implements the full ABC

**What remains is test cleanup:** Two duplicate fake implementations exist that need to be consolidated.

## Current Problem

### Duplicate Implementations

1. **`packages/erk-shared/src/erk_shared/integrations/gt/fake.py`**
   - Contains `GitHubState` dataclass (legacy)
   - Contains `FakeGitHubGtKitOps` class with note: "New tests should use FakeGitHub from erk_shared.github instead"

2. **`packages/dot-agent-kit/tests/unit/kits/gt/fake_ops.py`**
   - Contains duplicate `GitHubState` dataclass
   - Contains duplicate `FakeGitHubGtKitOps` class

3. **`FakeGtKitOps.github()` returns `FakeGitHubGtKitOps`** instead of the unified `FakeGitHub`

### Why This Matters

- Duplicated code (~500+ lines) across two files
- `FakeGitHubGtKitOps` doesn't implement the full `GitHub` ABC (uses `# type: ignore`)
- Inconsistent testing patterns between GT kit tests and other tests

## Implementation Plan

### Step 1: Extend FakeGitHub with Builder Pattern Support

**File:** `packages/erk-shared/src/erk_shared/github/fake.py`

Add constructor parameters to support GT-kit test scenarios:

- `pr_titles: dict[int, str]` - explicit PR title storage
- `pr_bodies_by_number: dict[int, str]` - explicit PR body storage
- `pr_diffs: dict[int, str]` - PR diff content
- `merge_should_succeed: bool` - control merge_pr() return value
- `pr_update_should_succeed: bool` - control update success

Add mutation tracking properties (some already exist):

- `updated_pr_titles` - track title updates

Modify existing methods:

- `get_pr_body()` - return from `pr_bodies_by_number` if set
- `merge_pr()` - respect `merge_should_succeed` flag

### Step 2: Create FakeGitHubBuilder or Extend FakeGtKitOps

**Option A: Add builder methods to FakeGtKitOps that configure FakeGitHub**

Keep `FakeGtKitOps` as the test helper with declarative builder methods, but have it create/configure a `FakeGitHub` instance instead of `FakeGitHubGtKitOps`.

The builder methods like `.with_pr()`, `.with_merge_failure()`, `.with_pr_conflicts()` will configure the `FakeGitHub` constructor parameters.

### Step 3: Update FakeGtKitOps.github() Return Type

**File:** `packages/dot-agent-kit/tests/unit/kits/gt/fake_ops.py`

Change:

```python
def github(self) -> FakeGitHubGtKitOps:  # type: ignore[override]
```

To:

```python
def github(self) -> FakeGitHub:
```

This requires modifying how the builder methods work since `FakeGitHub` uses constructor injection rather than mutable state.

### Step 4: Migrate Builder Pattern

The current `FakeGtKitOps` uses mutable builder pattern:

```python
ops = FakeGtKitOps().with_pr(123, state="OPEN").with_merge_failure()
```

The new approach needs to either:

- Accumulate state, then construct `FakeGitHub` on first `github()` call
- Or rebuild `FakeGitHub` on each builder method call

**Recommended:** Accumulate state in dataclass, construct `FakeGitHub` lazily.

### Step 5: Update Tests

**Files:**

- `packages/dot-agent-kit/tests/unit/kits/gt/test_submit_branch.py`
- `packages/dot-agent-kit/tests/unit/kits/gt/test_land_pr.py`
- `packages/dot-agent-kit/tests/unit/kits/gt/test_pr_update.py`
- `packages/dot-agent-kit/tests/unit/kits/gt/test_pr_prep.py`

Most tests should work unchanged if the builder API is preserved. May need adjustments for:

- Tests that call `ops.github().get_state()` - this method doesn't exist on `FakeGitHub`
- Tests that access `GitHubState` fields directly

Replace state assertions:

```python
# Before
github_state = ops.github().get_state()
assert github_state.pr_titles[123] == "New Title"

# After
assert ops.github().get_pr_title(repo_root, 123) == "New Title"
# Or use mutation tracking:
assert (123, "New Title", "body") in ops.github().updated_pr_bodies
```

### Step 6: Delete Legacy Code

**Files to modify:**

- `packages/erk-shared/src/erk_shared/integrations/gt/fake.py`
  - Delete `GitHubState` dataclass
  - Delete `FakeGitHubGtKitOps` class

**Files to delete:**

- None - `fake_ops.py` still needed for `FakeGitGtKitOps` and `FakeGtKitOps`

### Step 7: Update Exports

**File:** `packages/erk-shared/src/erk_shared/integrations/gt/__init__.py`

Remove any exports of `GitHubState` or `FakeGitHubGtKitOps` if present.

## Critical Files

| File                                                         | Action                                 |
| ------------------------------------------------------------ | -------------------------------------- |
| `packages/erk-shared/src/erk_shared/github/fake.py`          | Add constructor params, modify methods |
| `packages/dot-agent-kit/tests/unit/kits/gt/fake_ops.py`      | Rewrite FakeGtKitOps to use FakeGitHub |
| `packages/erk-shared/src/erk_shared/integrations/gt/fake.py` | Delete FakeGitHubGtKitOps, GitHubState |
| `packages/dot-agent-kit/tests/unit/kits/gt/test_*.py`        | Update state assertions (4 files)      |

## Testing Strategy

1. Run GT kit tests after each step to catch regressions
2. Ensure all existing builder method calls still work
3. Verify mutation tracking works for test assertions

## Risk Mitigation

- **Incremental migration:** Update FakeGitHub first, then migrate FakeGtKitOps
- **Test coverage:** Run full test suite after each change
- **Builder API preservation:** Keep the same `.with_*()` method signatures
