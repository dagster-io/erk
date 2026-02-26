# Documentation Plan: Delete GitHubPlanStore and PlanStore ABC, consolidate to PlanBackend interface

## Context

PR #8210 completes a significant interface consolidation: eliminating the PlanStore ABC and GitHubPlanStore implementation to establish PlanBackend as the sole abstract interface with PlannedPRBackend as its only implementation. This refactoring removed approximately 1,500 lines of deprecated code across 46 files, including ~696 lines of GitHubPlanStore implementation, ~959 lines of integration tests, and ~119 lines of unit tests for the deleted code.

The implementation revealed critical patterns for future ABC consolidation efforts. What appeared to be a straightforward "delete deprecated code" task exposed the complexity of cascading type annotation updates, test data model incompatibilities (IssueInfo vs PRDetails), and the need for conversion helpers to bridge incompatible abstractions. Future agents undertaking similar consolidation work will benefit from understanding the four-phase sequence discovered: inline abstract methods, change inheritance, cascade type annotations, and simplify dependent properties.

The test migration portion proved especially instructive. Direct mechanical replacement of `GitHubPlanStore(issues)` with `PlannedPRBackend(github, issues, time)` failed because the backends use fundamentally different data models. This led to creation of shared test utilities (`create_plan_store_with_plans`, `format_plan_header_body_for_test`, `_plan_to_pr_details`) that bridge the Plan/IssueInfo/PRDetails data model gap. These helpers represent reusable patterns for future test migrations.

## Raw Materials

Associated with PR #8210.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 14    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 4     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. Dual-backend testing guide (DELETE)

**Location:** `docs/learned/testing/dual-backend-testing.md`
**Action:** DELETE_STALE
**Phantom References:** References "dead code pending removal" for GitHubPlanStore patterns
**Cleanup Instructions:** Delete the entire document. It describes a transitional dual-backend state that PR #8210 completes. The document explicitly states GitHubPlanStore is "dead code pending removal" and recommends using PlannedPRBackend only - that transition is now complete.

### 2. Erk architecture PlanStore references (UPDATE)

**Location:** `docs/learned/architecture/erk-architecture.md` (lines 362-371)
**Action:** UPDATE_REFERENCES
**Phantom References:** `ctx.plan_store` vs `ctx.plan_backend` distinction; states "PlanBackend extends PlanStore"
**Cleanup Instructions:** Remove the ctx.plan_store vs ctx.plan_backend distinction. Update to describe PlanBackend as the sole interface (inherits from ABC directly, not from PlanStore). The plan_backend property is now a simple alias since plan_store field is typed as PlanBackend.

## Documentation Items

### HIGH Priority

#### 1. Consolidate overlapping migration docs

**Location:** `docs/learned/planning/plan-backend-migration.md` + `docs/learned/architecture/plan-backend-migration.md`
**Action:** UPDATE
**Source:** [Impl] + [PR #8210]

**Draft Content:**

```markdown
# Plan Backend Migration Guide

> **Migration Status:** COMPLETE as of PR #8210

This document consolidates migration guidance from the PlanStore era. The migration from GitHubPlanStore (issue-based) to PlannedPRBackend (PR-based) is complete.

## Current State

- **Interface:** PlanBackend (inherits from ABC)
- **Implementation:** PlannedPRBackend (sole implementation)
- **Deleted:** PlanStore ABC, GitHubPlanStore class

## For New Code

See erk_shared/plan_store/backend.py for the PlanBackend interface.
See erk_shared/plan_store/planned_pr.py for the PlannedPRBackend implementation.

Import patterns:
- PlanBackend from erk_shared.plan_store.backend
- PlannedPRBackend from erk_shared.plan_store.planned_pr

## Historical Migration Patterns

This section documents patterns used during the migration for reference in similar future consolidations.

### Test Migration Patterns

Three patterns emerged for migrating tests from GitHubPlanStore to PlannedPRBackend:

1. **Direct instantiation** - For tests constructing backends directly
2. **Helper functions** - For tests working with Plan objects
3. **FakeGitHub with pr_details** - For tests needing PR lookup behavior

See tests/test_utils/plan_helpers.py for shared helper implementations.
```

**Note:** Merge both existing files into a single authoritative guide. Remove transitional language and clearly mark the migration as complete.

#### 2. ABC consolidation pattern tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## ABC Consolidation

Before consolidating or deleting an ABC interface:

1. **Inline abstract methods FIRST** - Copy all abstract methods from the parent ABC into the child that will become the new sole interface
2. **Change inheritance SECOND** - Only after inlining, change the class to inherit from ABC directly
3. **Cascade type annotations THIRD** - Update all type annotations in: imports, dataclass fields, factory parameters, test utilities
4. **Simplify dependent properties FOURTH** - Properties that did isinstance() checks become direct returns

The sequence matters: doing step 2 before step 1 breaks all implementations. Doing step 4 before step 3 causes type errors.

See erk_shared/plan_store/backend.py for an example of a consolidated ABC.
```

#### 3. Type annotation cascading checklist tripwire

**Location:** `docs/learned/refactoring/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Type Annotation Cascading

Before changing a type used in frozen dataclass fields or ABC signatures:

Type changes cascade through multiple files. Check ALL of:
1. Import statements (add new, remove old)
2. Dataclass field type annotations
3. Function parameter type annotations
4. Local variable type annotations
5. Property return type annotations
6. Docstrings mentioning the old type

When the field name is common (store, client, gateway), use `replace_all=True` in Edit operations to catch all occurrences.

See erk_shared/context/context.py for an example of cascaded type updates.
```

#### 4. Test data model migration tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Test Data Model Migration

Before migrating tests between backends with different data models:

Check if backends use compatible data models. If BackendA uses DataTypeX and BackendB uses DataTypeY:

1. Create conversion helpers in tests/test_utils/ BEFORE starting mechanical refactoring
2. Validate approach on 2-3 representative files before bulk migration
3. Do NOT assume libcst-refactor can handle semantic changes (data model conversions)

Example: GitHubPlanStore used IssueInfo, PlannedPRBackend uses PRDetails. Direct replacement failed. Solution was create_plan_store_with_plans helper that converts Plan objects to PRDetails format.

See tests/test_utils/plan_helpers.py for the conversion helper pattern.
```

### MEDIUM Priority

#### 5. Plan test helpers documentation

**Location:** `docs/learned/testing/plan-test-helpers.md`
**Action:** CREATE
**Source:** [Impl] + [PR #8210]

**Draft Content:**

```markdown
---
read-when:
  - writing tests that construct Plan objects
  - setting up PlannedPRBackend in tests
  - converting between Plan and PRDetails formats
---

# Plan Test Helpers

The tests/test_utils/plan_helpers.py module provides utilities for testing with PlanBackend implementations.

## When to Use

- **create_plan_store_with_plans** - When tests construct Plan objects and need a backend. Returns tuple of (PlannedPRBackend, FakeGitHub) for mutation tracking.

- **format_plan_header_body_for_test** - When constructing test plan bodies with metadata. Creates plan header metadata body with sensible defaults.

## Implementation Notes

These helpers exist because PlannedPRBackend reads from FakeGitHub._pr_details (PRDetails format), but many tests naturally construct Plan objects. The helpers convert Plan to PRDetails format automatically.

See tests/test_utils/plan_helpers.py for implementation.
See tests/commands/pr/test_close.py for usage example.
```

#### 6. Architecture tripwires - Plan backend instantiation

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] + [PR #8210]

**Draft Content:**

```markdown
## Plan Backend Instantiation

CRITICAL: Always use PlannedPRBackend, never GitHubPlanStore (deleted in PR #8210).

Constructor signature: PlannedPRBackend(github, issues, time=...)

- **Production code:** Use create_minimal_context which constructs PlannedPRBackend automatically
- **Test code:** Inject via context_for_test(plan_store=...) or use create_plan_store_with_plans helper
- **Type annotations:** Use PlanBackend, not PlanStore (deleted)

See erk_shared/context/factories.py for production instantiation.
See erk_shared/context/testing.py for test instantiation.
```

#### 7. Testing tripwires - Import rules update

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] + [PR #8210]

**Draft Content:**

```markdown
## Plan Store Imports (Post PR #8210)

CRITICAL: Never import from deleted modules:
- erk_shared.plan_store.github (DELETED)
- erk_shared.plan_store.store (DELETED)

Correct imports:
- PlanBackend from erk_shared.plan_store.backend
- PlannedPRBackend from erk_shared.plan_store.planned_pr

Test pattern: Inject fake gateways into real backend (not fake backend):
```python
store = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())
```

Use create_plan_store_with_plans for Plan-object-based tests.

See tests/test_utils/plan_helpers.py for helper implementation.
```

#### 8. Testing tripwires - Batch migration pattern

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Batch Test Transformation

When refactoring affects many test files with similar patterns, consider a Python script with regex substitution instead of manual edits.

Pre-check each file for:
1. File existence
2. Already-migrated status (check for new pattern presence)
3. Actual need for migration (check for old pattern presence)

Maintain import order: Insert new imports after the last similar import pattern to preserve logical grouping.

This pattern was used in PR #8210 to migrate 18+ exec script test files.
```

#### 9. Update gateway-vs-backend examples

**Location:** `docs/learned/architecture/gateway-vs-backend.md`
**Action:** UPDATE
**Source:** [PR #8210]

**Draft Content:**

The existing document references GitHubPlanStore. Update all examples to use PlannedPRBackend.

Key change: Replace any `GitHubPlanStore(issues, time)` examples with `PlannedPRBackend(github, issues, time)`. Note the additional `github` parameter - PlannedPRBackend needs the full GitHub gateway for PR operations, not just issues.

#### 10. Update backend-testing-composition

**Location:** `docs/learned/testing/backend-testing-composition.md`
**Action:** UPDATE
**Source:** [PR #8210]

**Draft Content:**

Note that PlanBackend is now the sole interface (no PlanStore ABC). Emphasize PlannedPRBackend as the sole implementation.

Update the composition pattern: backends now require (github, issues, time) not just (issues, time).

### LOW Priority

#### 11. Fake gateway auto-registration pattern

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## FakeGitHub PR Setup

When testing with PlannedPRBackend:

PlannedPRBackend calls github.get_pr() which reads from _pr_details. Seed test data as pr_details in FakeGitHub constructor, NOT as issues in FakeGitHubIssues.

FakeGitHub.create_pr() auto-registers in _pr_details, enabling seamless write-then-read test patterns without manual setup.

Use create_plan_store_with_plans helper to convert Plan objects to PRDetails format automatically.

See tests/test_utils/plan_helpers.py for implementation details.
```

#### 12. Plan backend consolidation architecture doc

**Location:** `docs/learned/architecture/plan-backend-consolidation.md`
**Action:** CREATE
**Source:** [Impl] + [PR #8210]

**Draft Content:**

```markdown
---
read-when:
  - understanding why PlanStore ABC was deleted
  - learning about interface consolidation decisions
  - reviewing plan storage architecture
---

# Plan Backend Consolidation

PR #8210 consolidated two abstract interfaces (PlanStore, PlanBackend) into one (PlanBackend).

## Architectural Decision

PlanStore ABC was an intermediate abstraction that only added confusion. It defined read operations while PlanBackend extended it with write operations. In practice, all code needed both read and write, making the separation unnecessary.

## Changes

- PlanBackend now inherits from ABC directly (not from PlanStore)
- Abstract methods from PlanStore (get_plan, list_plans, get_provider_name, close_plan) were inlined into PlanBackend
- GitHubPlanStore (issue-based implementation) was deleted
- PlannedPRBackend is the sole implementation

## Constructor Difference

- Old: GitHubPlanStore(github_issues, time)
- New: PlannedPRBackend(github, github_issues, time)

PlannedPRBackend needs the full GitHub gateway for PR operations, not just issues.

See erk_shared/plan_store/backend.py for the consolidated interface.
See erk_shared/context/context.py for the simplified plan_backend property.
```

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Analysis Paralysis in Refactoring

**What happened:** Agent spent 700+ lines analyzing migration complexity, exploring different approaches, tracing data flow through fakes, and planning parallelization strategies before taking action.
**Root cause:** Front-loading analysis on complex migrations doesn't reveal blockers faster than implementing a few representative files.
**Prevention:** For migrations touching 30+ files, validate approach on 2-3 representative files FIRST. If those reveal non-mechanical changes needed, reassess strategy before planning full-scale parallel execution.
**Recommendation:** ADD_TO_DOC (docs/learned/refactoring/scope-management.md)

### 2. Mismatched Test Data Models

**What happened:** PlannedPRBackend reads from github.get_pr() which requires PRDetails in FakeGitHub._pr_details, but tests seeded IssueInfo in FakeGitHubIssues.issues, causing lookup failures.
**Root cause:** Backend implementations used different data models (IssueInfo vs PRDetails) despite similar interfaces.
**Prevention:** Before migrating tests to new backend, verify the backend's data access patterns. Create conversion helpers to bridge incompatible models.
**Recommendation:** TRIPWIRE (score=4, added to testing/tripwires.md)

### 3. Mechanical Refactor Assumption

**What happened:** Planned to use libcst-refactor for "mechanical" import/constructor changes, but actual migration required test data restructuring, assertion rewrites, and semantic changes.
**Root cause:** Confusion between truly mechanical changes (rename, move) and semantic changes (different APIs, different data models).
**Prevention:** Distinguish mechanical from semantic refactors before choosing tools. Don't assume refactor agents can handle semantic migrations.
**Recommendation:** ADD_TO_DOC (docs/learned/refactoring/tripwires.md)

### 4. Edit Tool Multiple Matches

**What happened:** String `plan_store: PlanStore` appeared in multiple contexts (class field + method parameter), causing Edit tool uniqueness error.
**Root cause:** Common field names appear in multiple contexts within the same file.
**Prevention:** Include surrounding context (1-2 lines) in old_string; default to replace_all=True for common names like store, client, gateway.
**Recommendation:** CONTEXT_ONLY (low severity, tool-specific)

### 5. Edit Without Read

**What happened:** Attempted to edit file content at specific lines without reading the file first.
**Root cause:** Assumed Grep results were sufficient for editing.
**Prevention:** Always Read files before Edit, even after Grep. The Edit tool enforces this for safety.
**Recommendation:** CONTEXT_ONLY (low severity, enforced by tool)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. ABC Consolidation Pattern

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Destructive potential +1)
**Trigger:** Before consolidating or deleting an ABC interface
**Warning:** Inline abstract methods into parent BEFORE changing inheritance. Then cascade type annotation updates through: (1) imports, (2) dataclass fields, (3) factory parameters, (4) test utilities. Finally simplify dependent properties that did isinstance checks.
**Target doc:** `docs/learned/architecture/tripwires.md`

This pattern emerged clearly during the implementation. The sequence of operations matters critically - changing inheritance before inlining methods breaks all implementations. The agent documented an explicit four-phase approach: inline abstract methods, change inheritance, cascade types, simplify properties. This sequence applies to any ABC consolidation effort and the consequences of wrong ordering are severe (broken builds).

### 2. Type Annotation Cascading

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before changing a type used in frozen dataclass fields or ABC signatures
**Warning:** Type changes cascade through multiple files. Check: (1) import statements, (2) field type annotations, (3) function parameter types, (4) local variable types, (5) property return types, (6) docstrings. Use replace_all=True when field name is common (store, client, gateway).
**Target doc:** `docs/learned/refactoring/tripwires.md`

The implementation revealed how changing `PlanStore` to `PlanBackend` propagated through context modules, factory functions, test utilities, and docstrings. The checklist is predictable and cross-cutting, applying to any core type change in the codebase.

### 3. Test Data Migration with Incompatible Models

**Score:** 4/10 (Non-obvious +2, Silent failure +2)
**Trigger:** Before migrating tests between backends with different data models
**Warning:** Create conversion helpers in tests/test_utils/ before starting mechanical refactoring. Check if BackendA uses DataTypeX and BackendB uses DataTypeY. Validate approach on 2-3 files before bulk migration.
**Target doc:** `docs/learned/testing/tripwires.md`

This pattern caused significant debugging time. The session showed extended analysis because direct replacement failed silently (tests would compile but fail at runtime with PRNotFound). Creating helpers upfront (create_plan_store_with_plans, etc.) transformed an intractable bulk migration into a tractable one.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Fake Gateway Auto-Registration

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Specific to FakeGitHub, not cross-cutting enough for HIGH priority. If similar patterns appear in other fake gateways, could be promoted to a general "fake gateway data flow" tripwire.

### 2. Background Agent + Parallel Work

**Score:** 3/10 (Non-obvious +1, Repeated pattern +1, External tool quirk +1)
**Notes:** Session-specific optimization pattern: launch mechanical work in background agent, handle non-mechanical work in parallel. Generalizability unclear - may be more of a personal efficiency pattern than codebase tripwire.

### 3. Legacy Test Branch Cleanup

**Score:** 3/10 (Non-obvious +1, Cross-cutting +1, Silent failure +1)
**Notes:** When removing deprecated ABC, check context_for_test() for legacy branching logic that creates old implementations. Pattern appeared once; may not recur frequently unless more ABC consolidations happen.

### 4. Edit Tool Multiple Matches

**Score:** 2/10 (Non-obvious +1, Repeated pattern +1)
**Notes:** Tool-specific issue, already handled by adding context. Low severity as the tool provides clear error messages.
