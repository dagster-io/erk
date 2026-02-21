# Documentation Plan: Implement lazy tip sync for worktree pool to fix stale assignment state

## Context

This PR (#7756) implements lazy synchronization of worktree pool assignments with actual git branch state. The core problem was that users manually running `gt create` or `git checkout` in pool slots caused the recorded branch names in `pool.json` to diverge from actual worktree state. This led to incorrect eviction decisions in `find_inactive_slot()` and confusing user-facing errors.

The solution adds transparent sync logic that runs immediately after loading pool state, correcting mismatches before any allocation or eviction decisions are made. This eliminates confusing "Fixing stale state" warnings and prevents blocked allocations. The key architectural decision was to silently adapt to user behavior rather than warn about it -- erk now treats manual git/gt operations as valid and adjusts its state accordingly.

Documentation matters here because the lazy sync pattern establishes a new architectural approach in erk, the behavioral change removes user-facing warnings that tests previously relied on, and the timing constraint (sync before allocation) is critical but non-obvious. Future agents implementing state management or allocation logic need to understand both the pattern and the philosophy behind transparent correction.

## Raw Materials

PR #7756

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 8     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score2-3) | 0     |

## Documentation Items

### HIGH Priority

#### 1. Lazy Pool Assignment Sync Pattern

**Location:** `docs/learned/architecture/slot-pool-state-sync.md` (new file)
**Action:** CREATE
**Source:** [PR #7756]

**Draft Content:**

```markdown
---
read-when:
  - working with worktree pool state
  - implementing allocation or eviction logic
  - syncing state across multiple worktrees
tripwires: 2
---

# Slot Pool State Synchronization

## Overview

The slot pool tracks branch assignments in `pool.json`, but users can manually change branches via `git checkout` or `gt create`. This creates divergence between recorded and actual state. Lazy sync corrects this divergence before allocation decisions.

## The Sync Pattern

Sync runs immediately after loading pool state, before any allocation or eviction logic:

<!-- source: src/erk/cli/commands/slot/common.py, grep for "def sync_pool_assignments" -->

The `sync_pool_assignments` function compares recorded branch names against actual git state and updates divergent assignments.

## Edge Cases

The sync algorithm handles several special cases:

1. **Missing worktree paths**: Skip sync (worktree may be on different machine)
2. **Detached HEAD**: Skip sync (preserve recorded assignment, no branch to compare)
3. **Placeholder branches**: Skip sync (placeholder state is intentional)
4. **Matching branches**: Skip sync (already accurate)
5. **Changed branches**: Update `branch_name` only, preserve `assigned_at` timestamp

## I/O Optimization

The sync function only writes to disk when changes are detected:

<!-- source: src/erk/cli/commands/slot/common.py, grep for "if synced_count == 0" -->

This preserves `pool.json` mtime when state is already accurate, avoiding unnecessary disk writes.

## Integration Timing

**Critical constraint:** Sync must run BEFORE calling `find_branch_assignment` or `find_inactive_slot`. These functions rely on accurate pool state for correct decisions.

See `allocate_slot_for_branch` in `src/erk/cli/commands/slot/common.py` for the integration point.

## Return Type

The `PoolSyncResult` dataclass contains the synced state and count of corrections:

<!-- source: src/erk/cli/commands/slot/common.py, grep for "class PoolSyncResult" -->
```

---

#### 2. Transparent State Correction Behavioral Change

**Location:** `docs/learned/erk/slot-pool-architecture.md`
**Action:** UPDATE
**Source:** [PR #7756]

**Draft Content:**

```markdown
## State Synchronization

(Add this section after "Allocation Algorithm")

As of PR #7756, the slot pool performs lazy synchronization before allocation decisions. This corrects divergence between recorded and actual branch state.

### Philosophy: Adapt, Don't Complain

When users manually run `git checkout` or `gt create` in pool slots, erk no longer warns about stale state. Instead, it transparently updates `pool.json` to reflect reality.

**Previous behavior:**
- Warning: "Fixing stale state: checking out 'X' in erk-slot-Y (was 'Z')"
- Error on dirty worktrees: "Cannot checkout 'X' in erk-slot-Y: worktree has uncommitted changes"

**Current behavior:**
- Silent sync: Stale slot stays assigned to actual branch
- Target branch gets fresh slot allocation
- No warnings, no errors

### Cross-reference

See [Slot Pool State Synchronization](../architecture/slot-pool-state-sync.md) for implementation details.
```

---

#### 3. Architecture Tripwire: Sync Before Allocation

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7756]

**Draft Content:**

```markdown
## Slot Pool State Sync

- **Before using slot pool state for allocation or eviction decisions**: Always run `sync_pool_assignments` after loading pool state. Stale branch assignments break eviction logic and cause confusing allocation errors. See [slot-pool-state-sync.md](slot-pool-state-sync.md).

- **Before calling `find_branch_assignment` or `find_inactive_slot`**: These functions rely on accurate pool state. Run `sync_pool_assignments` first or eviction logic will operate on stale data. The sync is already integrated into `allocate_slot_for_branch` but must be added to any new allocation entry points.
```

---

#### 4. CLI Tripwire: Branch Checkout Behavioral Change

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7756]

**Draft Content:**

```markdown
## Branch Checkout

- **Before testing `erk branch checkout` with manual git/gt usage**: Transparent sync means stale slots stay assigned to actual branches. Target branch gets fresh slot allocation, not checkout in existing slot. Tests expecting "Fixing stale state" warnings or dirty-worktree errors are outdated.
```

---

### MEDIUM Priority

#### 5. I/O Optimization Test Pattern

**Location:** `docs/learned/testing/test-patterns.md`
**Action:** UPDATE
**Source:** [PR #7756]

**Draft Content:**

```markdown
## I/O Optimization Testing

### Testing mtime preservation

When functions optimize by skipping disk writes when no changes occur, verify the optimization with mtime checks:

<!-- source: tests/unit/cli/commands/slot/test_common.py, grep for "test_sync_does_not_save_when_unchanged" -->

Pattern:
1. Record initial file mtime
2. Call the function with inputs that should trigger no changes
3. Verify file mtime is unchanged (assert mtime_before == mtime_after)
```

---

#### 6. End-to-End Integration Test Pattern

**Location:** `docs/learned/testing/test-patterns.md`
**Action:** UPDATE
**Source:** [PR #7756]

**Draft Content:**

```markdown
## End-to-End Integration Testing

### Testing sync + downstream logic

When a sync operation affects downstream logic (e.g., eviction decisions), write end-to-end tests that verify the full chain:

<!-- source: tests/unit/cli/commands/slot/test_common.py, grep for "test_eviction_uses_synced_state" -->

Pattern:
1. Set up state with intentional divergence
2. Call the upstream function (sync)
3. Call the downstream function (eviction)
4. Verify downstream function operated on synced state, not original state
```

---

#### 7. Terminology Disambiguation: Branch Tip vs Stack Tip

**Location:** `docs/learned/glossary.md`
**Action:** UPDATE
**Source:** [PR #7756]

**Draft Content:**

```markdown
### branch tip

The current commit SHA that a git branch points to. Distinguished from "stack tip" which refers to the topmost branch in a Graphite stack. When discussing worktree pool synchronization, "tip sync" refers to syncing branch tips (commit SHAs), not stack positions.

See also: **stack tip**, **upstack**, **downstack**
```

---

#### 8. Explaining PRs Pattern

**Location:** `docs/learned/documentation/explaining-prs.md` (new file, optional)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - explaining a PR to users
  - writing PR descriptions
  - documenting implementation rationale
---

# Explaining PRs to Users

## Effective PR Explanation Structure

When asked "what does this PR do?" or "why is this part of objective X?", use this structure:

1. **Define the problem state**: Technical details of what was wrong
2. **Give concrete scenarios**: 2-3 user-facing situations that triggered issues
3. **Explain the mechanism**: What the code does technically
4. **Connect to outcomes**: How each scenario is now resolved
5. **Link to objective**: Why this fits the broader goal

## Example

From PR #7756 explanation session:

- **Problem**: `pool.json` diverged from actual git state when users ran manual `git checkout`
- **Scenarios**: Manual workflow causing "stale state" warnings, dirty worktrees blocking allocation
- **Mechanism**: `sync_pool_assignments` compares recorded vs actual branch state before allocation
- **Outcomes**: No more warnings, dirty worktrees no longer block, transparent correction
- **Objective**: Enables "stack-in-place" workflow where users can mix erk and manual git/gt operations
```

---

## Contradiction Resolutions

No contradictions detected. Verified existing documentation:

| Existing Doc | Status | Notes |
|--------------|--------|-------|
| docs/learned/erk/slot-pool-architecture.md | CLEAN | All 5 source references verified |
| docs/learned/architecture/multi-worktree-state.md | CLEAN | All 3 source references verified |
| docs/learned/erk/placeholder-branches.md | CLEAN | All 6 source references verified |

## Stale Documentation Cleanup

No stale documentation detected. All high-relevance documents passed phantom reference verification.

## Prevention Insights

No errors or failed approaches were discovered during implementation. The session analyzer reported that this was primarily an explanation session, not an implementation session with debugging. All automated reviews (dignified-code-simplifier, test-coverage, dignified-python, tripwires) passed cleanly.

## Tripwire Candidates

Four items meet the tripwire-worthiness threshold (score >= 4):

### 1. Lazy Sync Must Run Before Allocation Decisions

**Score:** 8/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Silent failure +2)
**Trigger:** Before using slot pool state for allocation or eviction decisions
**Warning:** Always run sync_pool_assignments after loading pool state. Stale branch assignments break eviction logic and cause confusing allocation errors.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the timing constraint is not obvious from reading the code. A developer might load pool state and immediately call `find_branch_assignment` without syncing, leading to incorrect results. The failure is silent -- no exceptions, just wrong slot assignments.

### 2. Transparent State Correction Philosophy

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** When implementing state validation that could show user warnings
**Warning:** Prefer transparent correction over user-facing warnings when users manually perform valid git/gt operations. Warnings create friction; automatic adaptation creates robustness.
**Target doc:** `docs/learned/planning/tripwires.md`

This represents a significant UX philosophy shift. Without this tripwire, a future developer might revert to warning-based approaches, creating user friction and inconsistent behavior.

### 3. Sync Edge Cases Are Not Errors

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before implementing sync logic for state managed across worktrees
**Warning:** Missing paths, detached HEAD, and placeholder branches are valid skip cases, not errors. Sync should silently skip these states and continue processing other assignments.
**Target doc:** `docs/learned/architecture/tripwires.md`

The edge case handling is counter-intuitive. A developer might expect missing paths to raise errors or detached HEAD to be a warning condition.

### 4. Branch Checkout Behavioral Change

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before testing erk branch checkout with manual git/gt usage
**Warning:** Transparent sync means stale slots stay assigned to actual branches. Target branch gets fresh slot allocation, not checkout in existing slot.
**Target doc:** `docs/learned/cli/tripwires.md`

Tests expecting the old "Fixing stale state" warnings will fail. This tripwire helps developers update test expectations correctly.

## Potential Tripwires

No items scored 2-3. All identified tripwire candidates scored 4 or higher.

## Attribution

| Agent/Source | Items Identified | Key Contributions |
|--------------|------------------|-------------------|
| Code Diff Analyzer | 13 | Inventory of all code changes, edge cases, behavioral changes, test coverage |
| Existing Docs Checker | 3 | Verified no stale docs, identified terminology overlap, confirmed new topics |
| Session Analyzer | 1 | PR explanation pattern, teaching observations |
| PR Comments Analyzer | 0 | No human review comments (automated reviews only) |
