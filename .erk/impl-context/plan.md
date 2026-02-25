# Documentation Plan: Change test default plan_store from GitHubPlanStore to PlannedPRBackend

## Context

PR #8111 implements a significant change to test infrastructure: switching the default plan store in test contexts from `GitHubPlanStore` (GitHub issues backend) to `PlannedPRBackend` (draft PRs backend). This aligns test behavior with production, where draft PRs are the primary plan storage mechanism.

The implementation affected 21 test files, with changes falling into four categories: simplified tests that removed explicit backend setup (6 files), tests that explicitly opted into GitHubPlanStore (9 files), tests that added the new `plan_store` parameter (2 files), and tests refactored to use Plan objects with PlannedPRBackend helpers (4 files). The work uncovered critical architectural insights about how the two plan store implementations differ in their branch resolution strategies.

Documentation is essential because future agents and developers need to understand: (1) when to use PlannedPRBackend vs GitHubPlanStore in tests, (2) the non-obvious behavior difference where GitHubPlanStore uses regex matching while PlannedPRBackend checks GitHub for actual PRs, and (3) the backwards-compatibility trigger where passing `issues=` explicitly forces GitHubPlanStore. Several tripwire-worthy patterns emerged where agents spent significant time diagnosing issues that could have been prevented with better documentation.

## Raw Materials

Session 229d85e9, Session ac990a3e (parts 1 and 2), PR #8111 diff analysis

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 15    |
| Contradictions to resolve      | 2     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Resolve Default Backend Contradiction in dual-backend-testing.md

**Location:** `docs/learned/testing/dual-backend-testing.md`
**Action:** UPDATE
**Source:** [PR #8111]

**Draft Content:**

```markdown
## Test Context Default Backend (Updated PR #8111)

After PR #8111, test contexts default to **PlannedPRBackend**, not GitHubPlanStore.

### Two context_for_test() Implementations

The codebase has two `context_for_test()` implementations:

1. **erk-shared** (`packages/erk-shared/src/erk_shared/context/testing.py`): Used for basic unit tests. Defaults to PlannedPRBackend.

2. **src/erk/core** (`src/erk/core/context.py`): Used for CLI tests requiring additional parameters (workspace, env). Also defaults to PlannedPRBackend as of PR #8111.

### Backwards Compatibility Pattern

When tests explicitly pass `issues=FakeGitHubIssues()`, the context factory detects this via `issues_explicitly_passed` and creates a GitHubPlanStore instead. This preserves compatibility for tests that seed issue data.

See `testing.py` for resolution logic.
```

---

#### 2. Plan Store Selection for "No Plan Found" Tests (TRIPWIRE)

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 229d85e9, Session ac990a3e-part1

**Draft Content:**

```markdown
### Plan Store Selection for "No Plan Found" Tests

**CRITICAL: Tests asserting "no plan found" require explicit GitHubPlanStore with PlannedPRBackend default.**

After PR #8111, test contexts default to PlannedPRBackend, which treats **every PR as a plan**. Tests that assert "No linked plan found" will fail because PlannedPRBackend calls `github.get_pr_for_branch()` and finds the test's PR.

**To test "no plan found" scenarios:**

```python
from erk_shared.testing.fakes import FakeGitHubIssues
from erk_shared.plan_store.github_issue_store import GitHubPlanStore

# Explicit opt-in to GitHubPlanStore
ctx = context_for_test(
    issues=FakeGitHubIssues(),  # triggers GitHubPlanStore via issues_explicitly_passed
    plan_store=GitHubPlanStore(FakeGitHubIssues())  # or pass directly
)
```

**Why:** GitHubPlanStore uses regex matching on branch names (`plnd/...`). Non-matching branches like "feature" return PlanNotFound. PlannedPRBackend checks GitHub for actual PRs.

**Source:** `packages/erk-shared/src/erk_shared/context/testing.py:184-195`
```

---

#### 3. Update Backend Migration Documentation

**Location:** `docs/learned/planning/plan-backend-migration.md`
**Action:** UPDATE
**Source:** [PR #8111]

**Draft Content:**

```markdown
## Test Context Default Behavior (Updated PR #8111)

### Current Default

`ErkContext.for_test()` and `context_for_test()` now default to **PlannedPRBackend**, not GitHubPlanStore.

### Backwards Compatibility Trigger

Passing `issues=` parameter explicitly forces GitHubPlanStore:

```python
# Default: PlannedPRBackend
ctx = context_for_test()

# Explicit issues= triggers GitHubPlanStore
ctx = context_for_test(issues=fake_issues)
```

The `issues_explicitly_passed` detection logic in `context_for_test()` checks if the caller passed an issues gateway and routes to GitHubPlanStore for backwards compatibility.

### Migration Guide

- **New tests**: Use default (PlannedPRBackend) unless testing issue-specific behavior
- **Tests with pre-seeded issues**: Pass `issues=` to trigger GitHubPlanStore
- **"No plan found" tests**: Must use GitHubPlanStore explicitly (see testing/tripwires.md)
```

---

#### 4. issues vs github_issues Parameter Naming (TRIPWIRE)

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 229d85e9

**Draft Content:**

```markdown
### Parameter Naming: issues vs github_issues

**CRITICAL: Use `issues=`, not `github_issues=` when passing fake gateway to context builders.**

The test context builder chain uses `**kwargs` forwarding:

`build_workspace_test_context(**kwargs)` -> `env.build_context(**kwargs)` -> `context_for_test(**kwargs)`

The **final function signature** (`context_for_test`) determines valid parameter names. Common errors:

| Incorrect | Correct |
|-----------|---------|
| `github_issues=FakeGitHubIssues()` | `issues=FakeGitHubIssues()` |
| `git_gateway=FakeGit()` | `git=FakeGit()` |

**Error you'll see:** `TypeError: context_for_test() got an unexpected keyword argument 'github_issues'`

**Check:** Read `context_for_test()` signature in `src/erk/core/context.py` to confirm parameter names.
```

---

#### 5. Context Builder Kwargs Chaining

**Location:** `docs/learned/testing/context-builder-kwargs.md`
**Action:** CREATE
**Source:** [Impl] Session 229d85e9, Session ac990a3e-part2

**Draft Content:**

```markdown
# Test Context Builder Kwargs Flow

## Delegation Chain

Test context builders use `**kwargs` to delegate parameters through multiple layers:

```
build_workspace_test_context(**kwargs)
    -> env.build_context(**kwargs)
        -> context_for_test(**kwargs)
```

This allows callers to override any dependency at the top level.

## Parameter Name Resolution

The **final function in the chain** determines valid parameter names. When passing parameters to `build_workspace_test_context`, check `context_for_test()` signature.

## Examples

```python
# All these parameters flow to context_for_test()
ctx = build_workspace_test_context(
    workspace=ws,
    issues=fake_issues,        # -> context_for_test(issues=...)
    plan_store=custom_store,   # -> context_for_test(plan_store=...)
)
```

## Common Mistakes

See testing/tripwires.md for parameter naming errors (`github_issues` vs `issues`).

**Source:** `src/erk/core/context.py:195-312`
```

---

### MEDIUM Priority

#### 6. Plan Store Migration Guide

**Location:** `docs/learned/testing/plan-store-migration-guide.md`
**Action:** CREATE
**Source:** [PR #8111]

**Draft Content:**

```markdown
# Test Plan Store Migration Guide

## When to Use Each Backend

| Scenario | Backend | How to Configure |
|----------|---------|------------------|
| Default (new tests) | PlannedPRBackend | Do nothing, it's the default |
| Pre-seeded issue data | GitHubPlanStore | Pass `issues=FakeGitHubIssues()` |
| "No plan found" assertions | GitHubPlanStore | Must pass explicitly |
| Plan metadata/label tests | Either | Depends on what you're testing |
| PR-based plan lookup tests | PlannedPRBackend | Use default or pass explicitly |

## Migration Examples from PR #8111

### Simplified (6 files)

Tests that were backend-agnostic removed explicit setup:

```python
# Before: explicit backend
ctx = context_for_test(plan_store=GitHubPlanStore(fake))

# After: use default
ctx = context_for_test()
```

### Opt-in to GitHubPlanStore (9 files)

Tests with seeded issue data added explicit parameter:

```python
ctx = context_for_test(
    issues=fake_issues,
    plan_store=GitHubPlanStore(fake_issues)
)
```

### Plan Object Pattern (4 files)

Tests migrated from FakeGitHubIssues to Plan objects. See plan-object-patterns.md.

**Source:** PR #8111 diff
```

---

#### 7. Plan Object Test Pattern

**Location:** `docs/learned/testing/plan-object-patterns.md`
**Action:** CREATE
**Source:** [PR #8111]

**Draft Content:**

```markdown
# Plan Object Test Patterns

## Creating Plan Objects with PlannedPRBackend

Use `create_plan_store_with_plans()` helper pattern to seed plans:

```python
def create_plan_store_with_plans(plans: list[Plan]) -> tuple[PlannedPRBackend, FakeGitHub]:
    fake_github = FakeGitHub()
    backend = PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime())

    for plan in plans:
        backend.create_plan(
            repo_root=Path("/repo"),
            title=plan.title,
            content=plan.content,
            labels=plan.labels,
            metadata=plan.metadata,
        )

    return backend, fake_github
```

## Migration from FakeGitHubIssues

| Old Pattern | New Pattern |
|-------------|-------------|
| Create FakeGitHubIssues with issue data | Create Plan objects with backend.create_plan() |
| Seed issue_info dicts | Create Plan dataclass instances |
| Assert on issue API calls | Assert on plan behavior |

## Benefits

- Reduced coupling to GitHub issues API
- Cleaner test structure (~200 lines removed in migrations)
- Matches production behavior where plans are draft PRs

**Source:** `tests/unit/cli/commands/test_implement_shared.py:17-34`
```

---

#### 8. Update CLI Testing Patterns

**Location:** `docs/learned/testing/cli-testing.md`
**Action:** UPDATE
**Source:** [PR #8111]

**Draft Content:**

```markdown
## Plan Store Parameter in CLI Tests

`ErkContext.for_test()` and `context_for_test()` accept a `plan_store` parameter:

```python
ctx = ErkContext.for_test(
    plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime())
)
```

### Default Behavior (PR #8111+)

- Default: PlannedPRBackend
- Backwards compatibility: passing `issues=` explicitly triggers GitHubPlanStore

### When to Override

- Testing specific backend behavior
- Testing "no plan found" scenarios (requires GitHubPlanStore)
- Integration tests with specific plan configurations

**Source:** `packages/erk-shared/src/erk_shared/context/context.py:209-212`
```

---

#### 9. Conditional Feature Import Pattern

**Location:** `docs/learned/architecture/conditional-feature-imports.md`
**Action:** CREATE
**Source:** [PR #8111]

**Draft Content:**

```markdown
# Conditional Feature Imports for Backwards Compatibility

## Pattern

When adding backwards compatibility that requires conditional behavior based on parameter presence:

```python
def factory_function(
    *,
    new_param: SomeType | None = None,
    legacy_param: LegacyType | None = None,
):
    # Detect if legacy parameter was explicitly passed
    legacy_explicitly_passed = legacy_param is not None

    if new_param is not None:
        resolved = new_param
    elif legacy_explicitly_passed:
        # Inline import to avoid circular dependency / unnecessary load
        from erk.legacy import LegacyImplementation
        resolved = LegacyImplementation(legacy_param)
    else:
        resolved = DefaultImplementation()
```

## Example: issues_explicitly_passed

In `context_for_test()`:

```python
issues_explicitly_passed = github_issues is not None

if plan_store is not None:
    resolved_plan_store = plan_store
elif issues_explicitly_passed:
    # Caller seeded issue data
    from erk_shared.plan_store.github_issue_store import GitHubPlanStore
    resolved_plan_store = GitHubPlanStore(resolved_issues, FakeTime())
else:
    resolved_plan_store = PlannedPRBackend(...)
```

## Automated Review Note

This pattern may be flagged by automated reviews as "conditional imports" violation. This is a false positive when the import is for backwards compatibility routing, not feature detection.

**Source:** `packages/erk-shared/src/erk_shared/context/testing.py:184-195`
```

---

#### 10. Test Helper Consolidation Pattern

**Location:** `docs/learned/testing/test-helper-consolidation.md`
**Action:** CREATE
**Source:** [PR #8111]

**Draft Content:**

```markdown
# Test Helper Consolidation Pattern

## When to Consolidate

Consolidate duplicate test helpers when:

- Multiple functions create similar test fixtures
- Helper names differ but behavior overlaps
- Code review suggests duplication

## Example from PR #8111

Before (two helpers):

```python
def _make_issue_info(number: int, title: str) -> dict: ...
def _plan_header_body(title: str, content: str) -> tuple: ...
```

After (one consolidated helper):

```python
def _create_backend_with_plan(title: str, content: str) -> PlannedPRBackend: ...
```

## Process

1. Identify overlapping helpers in the same test module
2. Determine common abstraction (e.g., "create test plan")
3. Create unified helper with clear name
4. Update all call sites
5. Remove old helpers

This consolidation emerged from dignified-code-simplifier review feedback.
```

---

#### 11. Changing Test Context Defaults Pattern (POTENTIAL TRIPWIRE)

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session ac990a3e-part2

**Draft Content:**

```markdown
### Changing Test Context Defaults

**When changing default implementations in context_for_test():**

1. Grep for tests that assert negative conditions:
   - "not found"
   - "no plan"
   - "does not exist"

2. These tests may rely on old default behavior

3. Run full test suite, not just affected module

**Example:** PR #8111 changed default from GitHubPlanStore to PlannedPRBackend. Tests asserting "No linked plan found" broke because PlannedPRBackend treats all PRs as plans.

**Prevention:** Before changing infrastructure defaults, search for tests with negative assertions that might depend on the old behavior.
```

---

### LOW Priority

#### 12. Update Glossary Entry

**Location:** `docs/learned/glossary.md`
**Action:** UPDATE
**Source:** [PR #8111]

**Draft Content:**

```markdown
## context_for_test()

Test factory function that creates `ErkContext` instances with fake dependencies.

**Default backend:** PlannedPRBackend (as of PR #8111)

**Backwards compatibility:** Passing `issues=` explicitly triggers GitHubPlanStore.

**Two implementations exist:**
- `packages/erk-shared/src/erk_shared/context/testing.py` - basic tests
- `src/erk/core/context.py` - CLI tests with workspace support
```

---

#### 13. Document Two context_for_test() Implementations

**Location:** `docs/learned/testing/dual-backend-testing.md`
**Action:** UPDATE
**Source:** [PR #8111]

**Draft Content:**

```markdown
## Why Two context_for_test() Implementations?

### erk-shared Implementation

- **Location:** `packages/erk-shared/src/erk_shared/context/testing.py`
- **Purpose:** Basic unit tests without workspace dependencies
- **Parameters:** Core context parameters (issues, github, plan_store)

### src/erk/core Implementation

- **Location:** `src/erk/core/context.py`
- **Purpose:** CLI tests requiring workspace, environment, and additional erk-specific dependencies
- **Parameters:** All core parameters plus workspace, env, executor

### When to Use Each

- Use erk-shared for isolated unit tests
- Use src/erk/core for CLI command tests and integration tests
```

---

#### 14. Automated Review Architecture

**Location:** `docs/learned/ci/automated-review-workflow.md`
**Action:** CREATE
**Source:** [PR #8111]

**Draft Content:**

```markdown
# Automated Review Workflow

## Multi-Tier Review System

PR validation uses multiple automated reviewers:

1. **Test Coverage Review**: Checks for test presence
2. **Dignified Code Simplifier**: Suggests consolidation, cleanup
3. **Dignified Python**: Enforces coding standards
4. **Tripwires Review**: Checks for pattern violations

## Iterative Revalidation

When issues are addressed, reviewers revalidate:

1. Agent addresses feedback
2. Commit pushed
3. Reviewers re-run
4. Process repeats until clean

## Self-Correction Pattern

Reviewers may initially flag patterns as violations, then self-correct after analysis:

- PR #8111: Conditional imports initially flagged, then cleared after understanding backwards compatibility purpose
- This is normal behavior for context-dependent rules

## Convergence

Reviews converge when:
- All actionable items addressed
- No new violations introduced
- Revalidation passes
```

---

#### 15. Tripwires vs Coding Standards Distinction

**Location:** `docs/learned/reviews/review-architecture.md`
**Action:** UPDATE
**Source:** [PR #8111]

**Draft Content:**

```markdown
## Tripwires vs Coding Standards

### Coding Standards

General rules that apply to all code:
- LBYL not EAFP
- Frozen dataclasses
- No default parameters

Violations are style/pattern issues.

### Tripwires

Context-specific warnings for non-obvious pitfalls:
- "Tests asserting 'no plan found' need GitHubPlanStore"
- "Use `issues=` not `github_issues=`"

Violations may cause functional bugs.

### In Reviews

- Coding standards: Always flag
- Tripwires: Flag when action pattern matches trigger
```

---

## Contradiction Resolutions

### 1. Default Backend Discrepancy

**Existing doc:** `docs/learned/testing/dual-backend-testing.md`
**Conflict:** Doc states "only the 'planned_pr' backend exists" but doesn't document that BOTH context_for_test() implementations now default to PlannedPRBackend or the backwards compatibility trigger.
**Resolution:** Update doc with complete default behavior, two-implementation split explanation, and backwards compatibility pattern (items #1, #13).

### 2. Backend Selection Logic Documentation

**Existing doc:** `docs/learned/planning/plan-backend-migration.md`
**Conflict:** States "ErkContext.for_test(github_issues=fake_gh) automatically creates GitHubPlanStore" but new behavior is default PlannedPRBackend unless `issues=` explicitly passed.
**Resolution:** Update migration doc to clarify new default behavior and migration guide (item #3).

---

## Stale Documentation Cleanup

No stale documentation found with phantom references. All referenced code artifacts were verified to exist.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Parameter Name Mismatch in kwargs Chain

**What happened:** Agent tried `github_issues=FakeGitHubIssues()` but got TypeError because the final function (`context_for_test`) expects `issues=`.
**Root cause:** Plan wording used `github_issues` but actual parameter name differs. With `**kwargs` forwarding, the final function signature determines valid names.
**Prevention:** Always check final function signature when passing kwargs through delegation chains.
**Recommendation:** TRIPWIRE (item #4)

### 2. Test Failure from Infrastructure Default Change

**What happened:** `test_pr_submit_shows_no_plan_message` broke after commit ff1863fdc changed default plan_store.
**Root cause:** Test asserted "No linked plan found" but PlannedPRBackend treats all PRs as plans, making "no plan" impossible.
**Prevention:** When changing infrastructure defaults, grep for tests with negative assertions that may rely on old behavior.
**Recommendation:** TRIPWIRE (item #11)

### 3. Metadata Key Writer/Reader Mismatch

**What happened:** `plan_save.py` wrote `trunk_branch` but `checkout_cmd.py` read `base_ref_name`.
**Root cause:** Key rename wasn't propagated to all readers.
**Prevention:** When renaming metadata keys, grep for both old and new names across all packages.
**Recommendation:** ADD_TO_DOC (one-time fix, documented in session)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Plan Store Selection for "No Plan Found" Tests

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before asserting "no plan found" in tests with PlannedPRBackend default
**Warning:** When testing "no plan found" scenarios, explicitly pass `plan_store=GitHubPlanStore(fake_issues)` because PlannedPRBackend treats all PRs as plans.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because the agent spent significant time diagnosing why a test that previously passed started failing. The root cause (PlannedPRBackend's PR-based lookup treating all PRs as plans) is non-obvious and affects any test that validates negative plan scenarios. Without this tripwire, future agents will repeat the same investigation.

### 2. issues vs github_issues Parameter Naming

**Score:** 4/10 (Non-obvious +2, Repeated pattern +1, External tool quirk +1)
**Trigger:** Before passing fake gateway to build_workspace_test_context or context_for_test
**Warning:** Use `issues=` parameter (not `github_issues=`) when passing to test context builders. Check final function signature to confirm parameter name.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because the error message (TypeError for unexpected kwarg) doesn't hint at the correct parameter name. Plans and documentation may use inconsistent naming, leading agents to try the wrong name first.

### 3. Changing Test Context Defaults

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +1)
**Trigger:** Before changing default implementations in context_for_test() or similar test infrastructure
**Warning:** When changing default implementations in context_for_test(), grep for tests that assert "not found", "no plan", etc. These tests may rely on old default behavior and will break.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy as a preventive measure for future infrastructure changes. The pattern of tests relying on implicit default behavior is common, and breaking tests can be difficult to diagnose when the change is upstream.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Metadata Key Writer/Reader Mismatch

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Mentioned in session but resolved as one-time fix. Pattern: grep for both old and new key names when refactoring metadata dictionaries. Would become tripwire if pattern repeats.

### 2. Plan Resolution Behavior Differs Between Implementations

**Score:** 2/10 (Non-obvious +2)
**Notes:** GitHubPlanStore uses regex on branch names, PlannedPRBackend uses PR lookup. Documented in session ac990a3e-part2. May become tripwire if confusion recurs. Currently LOW priority because most tests don't need to care about resolution strategy.
