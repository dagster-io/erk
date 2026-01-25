# Documentation Plan: Phase 2A: Branch Subgateway Steelthread

## Context

Phase 2A implements the "flatten subgateway" pattern for Git branch operations, wiring the existing GitBranchOps subgateway into the Git ABC as a `branch` property. This follows the identical pattern established in Phase 1 for worktree operations, demonstrating the pattern's reusability across the codebase.

The implementation removes the `git_branch_ops` field from ErkContext entirely, replacing direct field access with property-based subgateway access (`ctx.git.branch`). This is a breaking change that simplifies the API surface while maintaining full testability through FakeGit's linked mutation tracking. Future agents working with branch operations need to understand this new access pattern, and agents extending the gateway hierarchy need the documented pattern for consistency.

This documentation matters because the flatten subgateway pattern is now proven across two implementations (Worktree and Branch) and will be applied to additional subgateways (Phase 2B: Graphite branch ops). Without documentation, future implementers may revert to field-based composition or implement inconsistent patterns across the 5 gateway layers.

## Raw Materials

https://gist.github.com/schrockn/b2b288a3d2f1c850ce3152d147adc215

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 11    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score 2-3)| 1     |

## Documentation Items

### HIGH Priority

#### 1. ErkContext.git_branch_ops Field Removal Tripwire

**Location:** `docs/learned/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add tripwire: "Before accessing `ctx.git_branch_ops` or calling branch mutation methods like `create_branch`, `delete_branch`, `checkout_branch`" → "Use `ctx.branch_manager` instead. Branch mutation methods are in GitBranchOps sub-gateway, accessible only through BranchManager. Query methods (get_current_branch, list_local_branches, etc.) remain on ctx.git."

This tripwire prevents agents from attempting to access the removed `git_branch_ops` field and directs them to the correct abstraction layer.

---

#### 2. Inconsistent Subgateway Property Implementation Tripwire

**Location:** `docs/learned/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add tripwire: "Before adding a new subgateway property to any gateway ABC" → "Must implement in all 5 layers: abc.py (abstract property), real.py (returns real implementation), fake.py (returns linked fake for mutation tracking), dry_run.py (wraps underlying property), printing.py (wraps with printing delegation). Reference Phase 1 (Worktree) and Phase 2A (Branch) patterns."

This tripwire ensures consistent implementation across all gateway layers when adding new subgateway properties.

---

#### 3. Factory Consistency After Field Removal Tripwire

**Location:** `docs/learned/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add tripwire: "Before refactoring to remove gateway fields from ErkContext" → "Verify that all factory functions update consistently: `create_branch_manager()`, `create_minimal_context()`, `context_for_test()`, and all test context constructors. Global search+replace is insufficient; manually verify each factory signature."

This tripwire prevents partial refactoring that leaves stale factory signatures.

---

#### 4. Gateway ABC Implementation Checklist Update

**Location:** `docs/learned/architecture/gateway-abc-implementation.md`
**Action:** UPDATE (Sub-Gateway Pattern section)
**Source:** [Impl]

**Draft Content:**

Update existing "Sub-Gateway Pattern for Method Extraction" section with Phase 2A implementation details:

- Show abc.py: abstract property with TYPE_CHECKING guard
- Show real.py: return existing instance
- Show fake.py: create linked instance at init, return same instance
- Show dry_run.py: lazy wrap underlying property
- Show printing.py: wrap with printing delegation
- Reference implementations: Phase 1 (git.worktree), Phase 2A (git.branch)

---

#### 5. Git Branch Subgateway Migration Guide

**Location:** `docs/learned/architecture/git-branch-subgateway-migration.md`
**Action:** CREATE (new document)
**Source:** [Impl]

**Draft Content:**

Create comprehensive migration guide showing:
- Breaking change: `git_branch_ops` field removed from ErkContext
- Before/after code examples for direct field access
- Factory changes (git_branch_ops parameter removed)
- Test migration (FakeGit creates linked instances automatically)
- Why this change (fewer fields, consistent access, testability)

---

### MEDIUM Priority

#### 6. Flatten Subgateway Pattern Documentation

**Location:** `docs/learned/architecture/flatten-subgateway-pattern.md`
**Action:** CREATE (new document)
**Source:** [Impl]

**Draft Content:**

Document the reusable pattern:
- Pattern definition (property-based vs. field-based access)
- Benefits (reduced fields, consistent access, encapsulation)
- Implementation checklist (5-layer implementation requirements)
- Reference implementations (Phase 1 and 2A examples)

---

#### 7. Linked Mutation Tracking in Tests

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE (new section)
**Source:** [Impl]

**Draft Content:**

Add section on linked mutation tracking:
- How FakeGit creates linked FakeGitBranchOps at initialization
- Shared collections enable mutation tracking
- Test assertions can use either access path (subgateway or main fake)
- Best practice: use ctx.git.branch in both production and test code

---

#### 8. Learn Workflow Session Discovery

**Location:** `docs/learned/planning/learn-workflow.md`
**Action:** UPDATE (troubleshooting section)
**Source:** [Plan]

**Draft Content:**

Add troubleshooting section:
- Session ID vs. file path mapping explanation
- Why get-learn-sessions returns session_sources array
- Use session_sources[].path instead of planning_session_id
- Preprocessing session syntax (options after positional path)

---

#### 9. Preprocess-session Command Syntax

**Location:** `docs/learned/cli/erk-exec-commands.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

Add preprocess-session command reference:
- Correct syntax: `erk exec preprocess-session <LOG_PATH> [OPTIONS]`
- Options must come AFTER positional LOG_PATH argument
- Show correct and incorrect examples
- Note about Click argument parsing

---

### LOW Priority

#### 10. BranchManager Factory Documentation

**Location:** `docs/learned/architecture/gateway-hierarchy.md`
**Action:** UPDATE (BranchManager section)
**Source:** [Impl]

**Draft Content:**

Update BranchManager factory section:
- Remove reference to git_branch_ops parameter
- Show factory no longer accepts git_branch_ops
- Note that BranchManager accesses branch ops through self.git.branch internally

---

#### 11. Erk Architecture Patterns Section

**Location:** `docs/learned/architecture/erk-architecture.md`
**Action:** UPDATE (add flatten pattern section)
**Source:** [Impl]

**Draft Content:**

Add section on flatten subgateway pattern:
- Pattern definition and motivation
- Implementations: ctx.git.worktree, ctx.git.branch
- Reference to full documentation
- Link to objective #5292 (gateway facade optimization)

---

## Contradiction Resolutions

None detected. All existing documentation is consistent with the Phase 2A implementation. The tripwires, gateway hierarchy documentation, and gateway ABC implementation checklist all align with the flatten subgateway pattern.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Session File Path Mismatch

**What happened:** Attempted to find session file using `planning_session_id` from `get-learn-sessions` output, but the file didn't exist.

**Root cause:** The `planning_session_id` is metadata, but actual session files are named differently for local vs. remote execution.

**Prevention:** Use `session_sources[].path` from `get-learn-sessions` output instead of constructing paths from `planning_session_id`.

**Recommendation:** ADD_TO_DOC - Document in learn-workflow.md troubleshooting section.

### 2. Click Command Option Ordering

**What happened:** Command with options before positional argument failed with "unexpected extra arguments" error.

**Root cause:** Click expects positional arguments before option flags.

**Prevention:** Always place options AFTER positional arguments. Check `erk exec <command> -h` to verify order.

**Recommendation:** ADD_TO_DOC - Document correct syntax in erk-exec-commands.md.

### 3. Inconsistent Property Implementation Across Layers

**What happened:** Initially only abc.py and real.py had the `branch` property, causing type errors in fake/dry-run variants.

**Root cause:** Copying abc.py changes without systematically updating all 5 implementation layers.

**Prevention:** Use explicit checklist when adding ABC properties. Verify all 5 layers implement.

**Recommendation:** TRIPWIRE - Captured as tripwire candidate #2.

### 4. Type Errors from Removed Fields

**What happened:** After removing `git_branch_ops` from ErkContext, type errors appeared in factory functions.

**Root cause:** Global search+replace found field usages but didn't account for factory function signatures.

**Prevention:** When removing fields, manually audit all factory functions and test helpers.

**Recommendation:** TRIPWIRE - Captured as tripwire candidate #3.

---

## Tripwire Candidates

### 1. git_branch_ops Field Removal

**Score:** 6/10 (Breaking change: +2, Non-obvious: +2, Cross-cutting: +2)

**Trigger:** Before accessing `ctx.git_branch_ops` or calling branch mutation methods directly

**Warning:** Use `ctx.branch_manager` instead. Branch mutation methods are in GitBranchOps sub-gateway, accessible only through BranchManager.

**Status:** Tripwire-worthy - Completely removed field, affects multiple call sites, error message doesn't indicate migration path.

### 2. Inconsistent Subgateway Property Implementation

**Score:** 5/10 (Cross-cutting: +2, Non-obvious: +2, Subtle failure: +1)

**Trigger:** Before adding a new subgateway property to any gateway ABC

**Warning:** Must implement in all 5 layers (abc, real, fake, dry_run, printing).

**Status:** Tripwire-worthy - Partial implementation causes non-obvious type errors across different gateway variants.

### 3. Factory Consistency After Field Removal

**Score:** 5/10 (Multiple locations: +2, Non-obvious: +2, Silent failure: +1)

**Trigger:** Before refactoring to remove gateway fields from ErkContext

**Warning:** Verify all factory functions update consistently. Global search+replace insufficient.

**Status:** Tripwire-worthy - Factory functions spread across multiple modules; default parameters silently accept old signature.

---

## Potential Tripwires

### 1. Session ID vs. File Path Mapping

**Score:** 3/10 (Non-obvious: +2, Learn workflow specific: +1)

**Notes:** Affects only learn workflow. Could promote to tripwire if learn becomes more widely used, but troubleshooting doc section sufficient for now.

---

## Summary by Action Type

**New Documentation to Create:** 4 docs
- `docs/learned/architecture/flatten-subgateway-pattern.md`
- `docs/learned/architecture/git-branch-subgateway-migration.md`
- `docs/learned/testing/testing.md` (linked mutation tracking section)
- `docs/learned/architecture/erk-architecture.md` (flatten pattern section)

**Existing Documentation to Update:** 7 docs
- `docs/learned/architecture/gateway-abc-implementation.md`
- `docs/learned/tripwires.md` (3 new tripwire entries)
- `docs/learned/architecture/gateway-hierarchy.md`
- `docs/learned/testing/testing.md`
- `docs/learned/planning/learn-workflow.md`
- `docs/learned/cli/erk-exec-commands.md`

**No Action Needed:** 6 items (already documented or internal maintenance)

---

## Key Insights

1. **Breaking change properly scoped:** The removal of `ctx.git_branch_ops` is well-contained within the subgateway property pattern. No code creates new instances; all paths use the shared property.

2. **Pattern reusability verified:** Phase 1 (Worktree) pattern successfully applied to Phase 2A (Branch). This confirms reusability and should be documented formally.

3. **Prevention insights valuable:** Session analysis uncovered concrete troubleshooting patterns (session ID mapping, command syntax) worth documenting.

4. **Test infrastructure simplified:** FakeGit's automatic linked mutation tracking removes manual test boilerplate, a positive outcome worth documenting.

5. **No contradictions:** All existing documentation aligns well with the implementation. No conflicting guidance detected.