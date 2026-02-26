# Documentation Plan: Consolidate plan saving to planned-PR backend only

## Context

PR #8229 consolidated erk's plan saving infrastructure from two backends (issue-based and planned-PR) to a single planned-PR backend. This involved deleting `RealPlanListService`, the `plan-save-to-issue` CLI command, and refactoring `RealObjectiveListService` to fetch objectives directly via the GitHub gateway rather than delegating to the now-deleted plan list service. The change removed 2,363 lines of code while adding only 165 lines.

The implementation revealed critical patterns around test migration when consolidating service backends. Thirty tests failed simultaneously because they provided data through the deleted `FakeGitHubIssues` pathway rather than the new `FakePlanListService`. Additionally, metadata filtering tests failed silently because `Plan.header_fields` must be explicitly populated in test-constructed Plan objects. These patterns are non-obvious and cross-cutting, making them prime candidates for documentation and tripwires.

The sessions also surfaced important external API quirks: GitHub's REST API returns comment IDs (`PRRC_*`) while thread resolution requires thread IDs (`PRRT_*`) from GraphQL. Shell quoting issues with JSON piping required switching from `echo` to heredoc patterns. These practical insights will prevent repeated debugging cycles for future agents.

## Raw Materials

PR #8229

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 22    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 8     |
| Potential tripwires (score2-3) | 4     |

## Documentation Items

### HIGH Priority

#### 1. RealObjectiveListService Direct Fetching Pattern

**Location:** `docs/learned/architecture/objective-list-direct-fetching.md`
**Action:** CREATE
**Source:** [PR #8229]

**Draft Content:**

```markdown
---
read-when:
  - instantiating RealObjectiveListService
  - implementing direct GitHub fetching for service classes
  - understanding objective vs plan data pathways
tripwires: 1
---

# RealObjectiveListService Direct Fetching Pattern

## Overview

RealObjectiveListService fetches objectives directly via the GitHub gateway instead of delegating to a plan list service. This pattern emerged during the plan backend consolidation (#8229).

## Constructor Signature

The constructor takes only the GitHub gateway and time abstraction:

See `src/erk/core/services/objective_list_service.py`, class `RealObjectiveListService.__init__`

Key points:
- No `GitHubIssues` parameter (removed in #8229)
- Uses `GitHub.get_issues_with_pr_linkages()` for fetching
- Includes timing instrumentation for performance monitoring

## Data Flow

1. Query GitHub issues with `erk-objective` label
2. Convert issues to Plan objects via `issue_info_to_plan()`
3. Optionally fetch workflow runs via node ID batch lookup
4. Return `PlanListData` with timing metrics (api_ms, plan_parsing_ms, workflow_runs_ms)

## Error Handling

Workflow run fetching uses broad exception handling because it's non-critical enrichment. Failures are logged and gracefully degraded rather than propagating to callers.

See `src/erk/core/services/objective_list_service.py` for the error handling pattern.

## Tripwires

- Before instantiating RealObjectiveListService with a GitHubIssues parameter, note the constructor signature changed in #8229
```

---

#### 2. Test Data Routing After Backend Consolidation

**Location:** `docs/learned/testing/backend-consolidation-test-migration.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - consolidating service backends
  - deleting ABC implementations
  - debugging "no data found" test failures after refactoring
tripwires: 2
---

# Test Data Routing After Backend Consolidation

## Problem

When consolidating from multiple backend implementations to a single backend, tests that provided data through the deleted backend's fake will fail with "no data found" errors.

## Symptom

Tests fail with messages like "No plans found matching the criteria" even though they populate `FakeGitHubIssues`/`FakeGitHub`. The command fetches via a different service abstraction that defaults to an empty fake.

## Root Cause

Commands route through an ABC → real service → gateway. When the real service implementation changes, tests must provide data through the correct fake:

- **Before**: Tests populated `FakeGitHubIssues`, fetched via `RealPlanListService`
- **After**: Command uses `plan_list_service` which defaults to empty `FakePlanListService()`

## Migration Steps

1. **Identify the new service abstraction** the command uses
2. **Add filtering logic to the fake service** to match real service behavior (state, labels, limit)
3. **Create a test helper** to reduce boilerplate:

   See `tests/test_utils/context_builders.py`, function `build_fake_plan_list_service`

4. **Update tests** to inject the fake service into context builders

## Example: Plan List Service Consolidation (#8229)

After deleting `RealPlanListService`, 30+ tests failed. The fix:

See `packages/erk-shared/src/erk_shared/core/fakes.py`, class `FakePlanListService.get_plan_list_data` for filtering implementation.

## Tripwires

- After deleting an ABC implementation, grep for all test references to the deleted class AND its fake data providers
- When many tests fail simultaneously with "no data found", check if tests are providing data through a deleted pathway
```

---

#### 3. Plan.header_fields in Tests

**Location:** `docs/learned/testing/plan-metadata-in-tests.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - writing tests that filter or display plan metadata
  - debugging lifecycle stage filters returning no results
  - constructing Plan objects in tests
tripwires: 1
---

# Plan Metadata Parsing in Tests

## Problem

Tests create `Plan` objects with metadata embedded in body YAML, but filters/display logic returns empty results or "-" placeholders.

## Root Cause

The `Plan` dataclass has a `header_fields: dict[str, object]` attribute that defaults to an empty dict. Real services parse the body YAML into this dict, but test-constructed Plans bypass parsing.

## Example: Lifecycle Stage Filter

Commands read metadata from `header_fields`, not from body text:

See `src/erk/core/lifecycle.py` for how `compute_lifecycle_display()` reads from `plan.header_fields`.

## Solution

Populate `header_fields` when constructing Plan objects in tests:

```python
planned_plan = Plan(
    plan_identifier="1",
    body="""<!-- erk:metadata-block:plan-header -->
    ```yaml
    lifecycle_stage: planned
    ```
    """,
    header_fields={"lifecycle_stage": "planned"},  # Parsed metadata
)
```

## When Required

Any test that filters/sorts/displays metadata from plan-header blocks must populate `header_fields`:
- `lifecycle_stage` for `--stage` filter
- `objective_id` for objective filtering
- `last_dispatched_run_id` for workflow run columns

## Tripwires

- When tests filter/display plan metadata but get no results, check if Plan.header_fields is populated
```

---

#### 4. Batch Thread Resolution Heredoc Pattern

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add this tripwire:

```markdown
## JSON Piping to erk exec resolve-review-threads

**TRIGGER**: Using `echo` to pipe JSON to `erk exec resolve-review-threads`

**WARNING**: Use `cat <<'JSONEOF'` heredoc pattern instead. Echo with nested quotes causes JSON parsing failures.

**PATTERN**:
```bash
# BAD - Shell interprets nested quotes:
echo '[{"thread_id": "PRRT_xxx", "comment": "Fixed in commit abc"}]' | erk exec resolve-review-threads

# GOOD - Heredoc preserves JSON:
cat <<'JSONEOF' | erk exec resolve-review-threads
[{"thread_id": "PRRT_xxx", "comment": "Fixed in commit abc"}]
JSONEOF
```

**WHY**: Comment text often contains quotes. Shell quote escaping breaks when JSON contains nested quotes in string values.
```

---

#### 5. GraphQL Thread ID vs Comment ID

**Location:** `docs/learned/pr-operations/thread-resolution.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - resolving PR review threads programmatically
  - debugging "Could not resolve to PullRequestReviewThread" errors
  - working with GitHub review comments API
tripwires: 1
---

# GraphQL Thread ID vs Comment ID

## Problem

Thread resolution fails with "Could not resolve to PullRequestReviewThread" error.

## Root Cause

GitHub's REST API returns comment node IDs (`PRRC_*`) but the `resolveReviewThread` GraphQL mutation requires thread IDs (`PRRT_*`).

## Solution

Query for thread IDs via GraphQL:

```bash
gh api graphql -f query='
  {
    repository(owner: "owner", name: "repo") {
      pullRequest(number: 123) {
        reviewThreads(first: 100) {
          nodes {
            id
            isResolved
          }
        }
      }
    }
  }
' --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false) | .id'
```

This returns thread IDs like `PRRT_kwDOPxC3hc5w2k28` which work with `resolveReviewThread` mutation.

## Key Distinction

| Source | ID Format | Use Case |
|--------|-----------|----------|
| REST API `/pulls/:id/comments` | `PRRC_*` | Reading comment content |
| GraphQL `reviewThreads.nodes[].id` | `PRRT_*` | Thread resolution |

## Tripwires

- When thread resolution fails with 'Could not resolve to PullRequestReviewThread', you may be using comment IDs instead of thread IDs
```

---

#### 6. Source Pointer Verification Protocol

**Location:** `docs/learned/documentation/verification-protocols.md`
**Action:** CREATE
**Source:** [PR #8229]

**Draft Content:**

```markdown
---
read-when:
  - adding source pointers to documentation
  - referencing specific functions or files in docs
  - updating documentation after code changes
tripwires: 1
---

# Source Pointer Verification Protocol

## Overview

Before adding source pointers to documentation, verify they point to real, current code locations.

## Verification Steps

1. **Verify file paths with Glob**: Confirm the file exists at the documented path
2. **Confirm function locations with Grep**: Search for the function name to verify it exists
3. **Test CLI examples by executing them**: Run documented commands to verify syntax
4. **Check file existence for test references**: Ensure referenced test files weren't deleted

## Common Failures

| Failure Mode | Prevention |
|--------------|------------|
| File moved or renamed | Grep for function name, update path |
| Function renamed | Search for old and new names, update reference |
| Module restructured | Check import paths, update accordingly |
| Test file deleted | Remove reference or note deletion |

## Line Number References

NEVER use line number references in documentation. They go stale silently when code changes:

```markdown
# BAD - Goes stale silently:
See `src/foo.py` lines 45-67 for the implementation.

# GOOD - Function name is searchable:
See `src/foo.py`, function `handle_request` for the implementation.
```

## Tripwires

- Before adding source pointers to documentation, verify file paths with Glob, confirm function locations with Grep, test CLI examples by executing them
```

---

#### 7. Update Plan Creation Pathways

**Location:** `docs/learned/planning/plan-creation-pathways.md`
**Action:** UPDATE
**Source:** [PR #8229]

**Draft Content:**

Update the pathways table to:
- Remove `plan-save-to-issue` entry (command deleted in #8229)
- Add note referencing the consolidation: "See #8229 for backend consolidation details"
- Ensure all remaining pathways point to `plan-save` (planned-PR backend)

---

#### 8. Update Planned-PR Backend Documentation

**Location:** `docs/learned/planning/planned-pr-backend.md`
**Action:** UPDATE
**Source:** [PR #8229]

**Draft Content:**

Update to reflect completion:
- Change "will be removed" to "was removed in #8229"
- Update PLAN_BACKEND_SPLIT comment status to "removed"
- Add reference to PR #8229 as the consolidation PR
- Remove future-tense predictions that are now historical facts

---

### MEDIUM Priority

#### 9. FakePlanListService Filtering Pattern

**Location:** `docs/learned/testing/fake-service-filtering.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - implementing filtering logic in fake services
  - deciding whether fakes should filter or return pre-filtered data
  - debugging test failures related to fake service behavior
---

# Fake Service Filtering Implementation

## Decision: When to Add Filtering

Add filtering logic to fake services when:
- Tests verify filter behavior (e.g., `--stage planned` returns only planned items)
- Real service has non-trivial filtering that affects test correctness
- Multiple tests need consistent filtering semantics

Return pre-filtered data when:
- Tests only verify "something displays" without filter semantics
- Filtering logic would make the fake too complex
- Test data is already minimal

## Implementation Pattern

See `packages/erk-shared/src/erk_shared/core/fakes.py`, class `FakePlanListService.get_plan_list_data` for the reference implementation.

Key filters implemented:
- State filtering (open/closed) using PlanState enum
- Label filtering with AND logic (all labels must be present)
- Exclude labels (any excluded label removes the plan)
- Limit (truncate to first N results)

## Filter Execution Order

1. State filtering first (most selective)
2. Label filtering (AND logic)
3. Exclude labels
4. Limit (applied last)
```

---

#### 10. Exception Analysis Workflow

**Location:** `docs/learned/testing/exception-analysis-workflow.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - fixing bare except Exception blocks
  - determining correct exception types for catch blocks
  - investigating subprocess error handling
---

# Exception Analysis Workflow

## Problem

Linters flag bare `except Exception` as overly broad. Simply replacing with a narrower type without investigation can break error handling.

## Workflow

1. **Read the flagged code location**: Understand what operation can fail
2. **Trace the call chain**: Identify what functions are called and what they can raise
3. **Examine wrapper patterns**: Check if errors are normalized (e.g., subprocess wrappers that convert all failures to RuntimeError)
4. **Consider all failure modes**: List every exception type that could realistically occur
5. **Choose based on caller needs**: If callers don't branch on error type and all failures should be handled identically, broad catch may be appropriate

## Example: Workflow Run Fetching

The `get_workflow_runs_by_node_ids()` call chain:
- Calls `execute_gh_command_with_retry()`
- That wrapper normalizes all subprocess failures to `RuntimeError`
- JSON parsing could raise `JSONDecodeError` or `KeyError`
- Callers don't branch on error type

Resolution: `except RuntimeError` is appropriate because the subprocess wrapper normalizes failures, but if JSON parsing is in the try block, broader handling may be needed.

## When Broad Catch Is Appropriate

See `docs/learned/architecture/exception-handling-patterns.md` for resilience catch-all patterns.
```

---

#### 11. Pre-Implementation Verification Pattern

**Location:** `docs/learned/planning/pre-implementation-verification.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - starting implementation of a plan
  - arriving at an implementation branch
  - resuming work after session interruption
---

# Pre-Implementation Verification Pattern

## Problem

Work may have been partially or fully completed in a previous session. Starting implementation without checking wastes effort.

## Pattern

Before implementing plan steps:

1. **Read key files mentioned in the plan**: Check if changes are already made
2. **Run tests scoped to the changed files**: Verify current state
3. **Check git status and recent commits**: See what was already committed
4. **Report status**: If work is complete, skip to verification

## Benefits

- Avoids redundant implementation work
- Catches partial implementations that need completion
- Identifies merge conflicts or intervening changes

## Example

Session b37471e8 arrived at an implementation branch and discovered all plan steps were already complete by reading the key files first. This saved significant redundant work.
```

---

#### 12. False Positive Detection from Bot Reviews

**Location:** `docs/learned/review/false-positive-detection.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - addressing automated review bot comments
  - deciding whether to change code or dismiss a review comment
  - working with dignified-python-review feedback
---

# False Positive Detection from Bot Reviews

## Problem

Automated reviewers (dignified-python-review, linters, security scanners) flag code without full context. Not all flags require code changes.

## Verification Steps

Before making changes suggested by automated reviewers:

1. **Read the flagged code carefully**: Understand what the code actually does
2. **Check sibling implementations**: Is the same pattern used elsewhere intentionally?
3. **Reference project conventions**: Does project documentation explicitly allow this pattern?
4. **Consider pedagogical context**: Is this documentation showing an illustrative example vs verbatim code?

## Resolution Options

| Finding | Action |
|---------|--------|
| Genuine issue | Fix the code |
| False positive | Resolve thread with detailed explanation |
| Intentional pattern | Cite project convention in resolution |
| Illustrative example | Explain pedagogical intent |

## Example: Exception Handling False Positive

Bot flagged `except Exception` as too broad. Investigation revealed:
- Identical pattern at 3 other locations in sibling services
- Project docs explicitly allow broad catch for non-critical enrichment
- Resolution: Dismiss with explanation referencing conventions
```

---

#### 13. Zero-Commit PR Review Resolution

**Location:** `docs/learned/review/false-positive-resolution.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - resolving PR review threads without code changes
  - handling false positives from automated reviewers
  - writing resolution explanations
---

# Zero-Commit PR Review Resolution

## When to Use

Not all PR review cycles require code changes. Resolve without commits when:
- Review comment is a false positive
- Request is for clarification, not change
- Documentation shows intentional illustrative example
- Project convention explicitly allows the flagged pattern

## Resolution Requirements

When resolving without code changes:
- Provide detailed technical explanation
- Reference specific line numbers where the pattern is used
- Cite project conventions or documentation
- Explain why no change is needed

## Example Resolution

> This `except Exception` is intentional per project conventions. See `docs/learned/architecture/exception-handling-patterns.md` for the resilience catch-all pattern. The identical pattern appears at lines 293 and 336 in `plan_list_service.py`. This is non-critical enrichment where all failures should be logged and gracefully degraded.
```

---

#### 14. Update Exception Handling Patterns

**Location:** `docs/learned/architecture/exception-handling-patterns.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add section on when broad exception handling is acceptable:

```markdown
## Resilience Catch-All Pattern

Use `except Exception` for non-critical enrichment operations where:
1. The operation is optional (e.g., fetching workflow run metadata)
2. All failure modes should be handled identically (log warning, continue)
3. Multiple exception types are possible (RuntimeError, JSONDecodeError, KeyError)
4. Callers don't branch on error types

Example locations:
- Workflow run fetching in RealObjectiveListService
- Optional metadata enrichment in list commands

This contrasts with critical paths where specific exceptions should be caught and callers may need to handle different failure modes.
```

---

#### 15. Strengthen Documentation Core Rules

**Location:** `docs/learned/documentation/learned-docs-core.md`
**Action:** UPDATE
**Source:** [PR #8229]

**Draft Content:**

Add/strengthen these rules:

```markdown
## Private Method References

NEVER reference private methods (`_underscore_methods`) in documentation:
- Private methods can be renamed or removed without notice
- Their behavior belongs in docstrings, not docs
- Only reference stable public APIs and ABCs

## CLI Example Standards

CLI examples in documentation MUST be runnable or clearly marked as simplified:
- Test examples by executing them
- Include all required arguments
- Use actual output keys from the command
- Mark simplified examples: `<!-- example-type: illustrative -->`

## Section Heading Conventions

- **Concepts sections**: "What" and "Why" - high-level understanding
- **Implementation sections**: "How" - specific code patterns
- Separate conceptual understanding from implementation details
```

---

#### 16. Update Plan Mode Exit Workflow

**Location:** `docs/learned/planning/plan-mode-exit-workflow.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Clarify the marker creation and exit sequence:

```markdown
## Exit Plan Mode Workflow

When ExitPlanMode is blocked by the hook:

1. Hook displays three options: Save plan, Implement now, Cancel
2. User selects an option
3. If "Implement now": Create `implement-now` marker first
4. Then call ExitPlanMode again
5. Hook verifies marker exists before allowing exit

If ExitPlanMode is rejected after marker creation, check:
- Was the marker created successfully?
- Is the marker in the expected location?
- Did another hook intercept the call?
```

---

#### 17. Multi-Tier Review System Documentation

**Location:** `docs/learned/review/multi-tier-review-effectiveness.md`
**Action:** CREATE
**Source:** [PR #8229]

**Draft Content:**

```markdown
---
read-when:
  - understanding erk's review system
  - evaluating automated review effectiveness
  - configuring review bots
---

# Multi-Tier Review System

## Architecture

Erk uses a multi-tier review system:
1. **Mechanical checks**: Linters, formatters, type checkers (ruff, prettier, ty)
2. **LLM semantic review**: dignified-python-review bot checks code patterns
3. **Human review**: Final approval and context-aware decisions

## Effectiveness Observations

From PR #8229 (38 files, -2,198 net lines):
- Mechanical checks caught: formatting issues, lint violations
- LLM review caught: stale documentation references, naming inconsistencies
- False positives: ~15% of LLM comments required dismissal with explanation

## Signal-to-Noise Assessment

The multi-tier system provides high value despite false positives:
- Mechanical + LLM caught 4 legitimate drift issues
- False positives were identifiable with code context reading
- Resolution explanations document rationale for future reference
```

---

#### 18. Test Coupling to Implementation Anti-Pattern

**Location:** `docs/learned/testing/test-coupling-to-implementation.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - debugging mass test failures after refactoring
  - designing test data injection patterns
  - understanding test architecture
---

# Test Coupling to Implementation Anti-Pattern

## Problem

Tests that depend on specific implementation details rather than abstract interfaces break when implementations change.

## Example: Backend Consolidation

30 tests failed after deleting `RealPlanListService` because they:
- Provided data through `FakeGitHubIssues` (implementation detail)
- Instead of through `PlanListService` abstraction (stable interface)

When the implementation changed, all tests broke simultaneously despite the interface (`PlanListService`) remaining stable.

## Prevention

Design tests to inject data through abstract interfaces:

```python
# BAD - Coupled to implementation:
ctx = build_context(github_issues=fake_issues)  # Assumes specific service

# GOOD - Coupled to interface:
ctx = build_context(plan_list_service=fake_plan_service)  # Uses abstraction
```

## Benefits

- Tests survive implementation changes
- Easier to swap implementations
- Clearer test intent (what's being tested vs how)
```

---

### LOW Priority

#### 19. Update PR Operations Known Issues

**Location:** `docs/learned/pr-operations/known-issues.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add note about argument length limits:

```markdown
## update-pr-description Argument Length Limit

**Symptom**: `OSError: [Errno 7] Argument list too long: 'claude'`

**Cause**: PR diff exceeds subprocess argument length limit (~128KB) when passed to claude CLI.

**Affected**: PRs with >100 file changes or >100K diff characters

**Resolution**: Accept as non-critical. PR title/body can remain unchanged or be updated manually. This is an optional enhancement, not required for PR workflow.

**Future**: Consider stdin-based input for large diffs.
```

---

#### 20. Line Range References Tripwire

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8229]

**Draft Content:**

Add tripwire:

```markdown
## Line Range References in Documentation

**TRIGGER**: Adding line number references to documentation (`lines 45-67`, `line 123`)

**WARNING**: Line numbers go stale silently when code changes. Use function/class names instead.

**PATTERN**:
```markdown
# BAD:
See src/foo.py lines 45-67 for implementation.

# GOOD:
See src/foo.py, function handle_request for implementation.
```

**WHY**: Code changes shift line numbers without updating documentation. Function names are searchable and stable.
```

---

#### 21. Prettier Formatting After Table Edits

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add tripwire:

```markdown
## Prettier Formatting After Table Edits

**TRIGGER**: Manually editing markdown tables (adding/removing columns or rows)

**WARNING**: Run `prettier --write <file>` after editing. CI will fail without it.

**WHY**: Prettier enforces consistent table column widths. Manual edits break alignment.
```

---

#### 22. Update Plan List Provider Pattern Doc

**Location:** `docs/learned/cli/plan-list-provider-pattern.md`
**Action:** UPDATE_REFERENCES
**Source:** [PR #8229]

**Draft Content:**

Verify and update class references:
- Check if `RealPlanDataProvider` still exists or was renamed
- Update to `PlannedPRPlanListService` if that's the current implementation
- Remove any references to deleted `RealPlanListService`

---

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. Plan List Provider Pattern

**Location:** `docs/learned/cli/plan-list-provider-pattern.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `RealPlanDataProvider` (not found by Glob)
**Cleanup Instructions:** Verify if this class was renamed to `PlannedPRPlanListService` or search missed it. Update references to current class names.

### 2. Planned-PR Backend Documentation

**Location:** `docs/learned/planning/planned-pr-backend.md`
**Action:** UPDATE_EXISTING
**Phantom References:** "PLAN_BACKEND_SPLIT comment blocks" with future tense
**Cleanup Instructions:** Change "will be removed" to "was removed in #8229". Update all future-tense predictions to past-tense facts.

### 3. Plan Creation Pathways

**Location:** `docs/learned/planning/plan-creation-pathways.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `plan-save-to-issue` command
**Cleanup Instructions:** Remove the deleted command from the pathways table. All plan saving now goes through `plan-save`.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Mass Test Failures After Service Consolidation

**What happened:** 30 tests failed with "No plans found matching the criteria" after deleting `RealPlanListService`
**Root cause:** Tests provided data through `FakeGitHubIssues` which the deleted service consumed. The new `PlannedPRPlanListService` uses `FakePlanListService` which was empty.
**Prevention:** When deleting an ABC implementation, grep for all references to the deleted class AND its associated fake data providers. Update tests systematically.
**Recommendation:** TRIPWIRE

### 2. Thread Resolution 'NOT_FOUND' Error

**What happened:** `resolveReviewThread` mutation failed with "Could not resolve to PullRequestReviewThread"
**Root cause:** Used comment node IDs (`PRRC_*`) from REST API instead of thread IDs (`PRRT_*`) from GraphQL
**Prevention:** Query `reviewThreads.nodes[].id` via GraphQL for resolution, not REST API comment IDs
**Recommendation:** TRIPWIRE

### 3. Metadata Filter Returns No Results in Tests

**What happened:** Tests with `--stage planned` filter returned "No plans found" despite plans having the stage in body YAML
**Root cause:** `Plan.header_fields` defaults to empty dict. The `compute_lifecycle_display()` reads from `header_fields`, not body text.
**Prevention:** Populate `header_fields` when constructing Plans in tests
**Recommendation:** TRIPWIRE

### 4. JSON Parsing Failure with Echo Piping

**What happened:** `echo '[{"thread_id": "...", "comment": "..."}]' | erk exec resolve-review-threads` failed with JSON parsing error
**Root cause:** Shell interpreted nested quotes in comment text, corrupting the JSON
**Prevention:** Use heredoc pattern (`cat <<'JSONEOF'`) for multi-line JSON stdin
**Recommendation:** TRIPWIRE

### 5. False Positives from Automated Reviewers

**What happened:** Bot flagged `except Exception` as too broad, but the pattern was intentional
**Root cause:** Bots compare code snippets without understanding project conventions or pedagogical context
**Prevention:** Read code context and reference project conventions before accepting bot suggestions
**Recommendation:** ADD_TO_DOC

### 6. Stale Documentation References

**What happened:** Documentation referenced function names, line numbers, and file paths that no longer existed
**Root cause:** Documentation not verified against current codebase after code changes
**Prevention:** Grep to confirm file paths, function names, and test file existence before documenting
**Recommendation:** TRIPWIRE

### 7. CLI Examples Fail When Executed

**What happened:** Documentation examples used wrong output keys or missing arguments
**Root cause:** Examples written without testing execution
**Prevention:** Test CLI examples by executing them or mark as simplified with metadata
**Recommendation:** ADD_TO_DOC

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Backend Consolidation Test Data Routing

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** After deleting an ABC implementation, before running tests
**Warning:** Check all test files for dependencies on the deleted implementation's data pathways. Grep for the deleted class name AND associated fake data providers. Update tests systematically.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because backend consolidations are rare but when they happen, the test failures are cascading and non-obvious. The pattern of tests using deleted fake pathways isn't caught by the type system.

### 2. Batch Thread Resolution Heredoc Pattern

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +2)
**Trigger:** Before using echo to pipe JSON to erk exec resolve-review-threads
**Warning:** Use cat <<'JSONEOF' heredoc pattern instead. Echo with nested quotes causes JSON parsing failures.
**Target doc:** `docs/learned/pr-operations/tripwires.md`

The echo approach is the obvious choice but fails silently with complex JSON. This tripwire prevents repeated debugging of shell quoting issues.

### 3. Plan.header_fields Must Be Populated in Tests

**Score:** 5/10 (Non-obvious +2, Repeated pattern +2, Silent failure +1)
**Trigger:** When tests filter/display plan metadata but get no results
**Warning:** Check if Plan.header_fields is populated. Metadata must be in this dict, not just in body YAML.
**Target doc:** `docs/learned/testing/tripwires.md`

Tests can pass body YAML with metadata and still fail because filtering reads from `header_fields`. The default empty dict causes silent filtering failures.

### 4. GraphQL Thread ID vs Comment ID

**Score:** 5/10 (Non-obvious +2, External tool quirk +2, Silent failure +1)
**Trigger:** When thread resolution fails with 'Could not resolve to PullRequestReviewThread'
**Warning:** You may be using comment IDs (PRRC_*) instead of thread IDs (PRRT_*). Query reviewThreads.nodes[].id via GraphQL.
**Target doc:** `docs/learned/pr-operations/tripwires.md`

GitHub's API design makes this mistake easy. REST returns one ID type, GraphQL mutations need another.

### 5. RealObjectiveListService Constructor Signature

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before instantiating RealObjectiveListService with GitHubIssues parameter
**Warning:** Constructor signature changed: RealObjectiveListService(github: GitHub, *, time: Time). GitHubIssues parameter removed in #8229.
**Target doc:** `docs/learned/architecture/tripwires.md`

The type system will catch this at runtime, but a tripwire can prevent the confusion during development.

### 6. Source Pointer Verification Protocol

**Score:** 4/10 (Cross-cutting +2, Repeated pattern +2)
**Trigger:** Before adding source pointers to documentation
**Warning:** Verify file paths with Glob, confirm function locations with Grep, test CLI examples by executing them.
**Target doc:** `docs/learned/documentation/tripwires.md`

Documentation drift was a recurring theme across sessions. This tripwire enforces verification before adding references.

### 7. Test Coupling to Implementation Details

**Score:** 4/10 (Non-obvious +2, Destructive potential +2)
**Trigger:** When consolidating service implementations and many tests fail simultaneously
**Warning:** Tests may be coupled to specific implementation pathways. Inject data through abstract service interfaces, not implementation-specific fakes.
**Target doc:** `docs/learned/testing/tripwires.md`

This is the root cause of mass test failures during refactoring. The tripwire guides toward the correct fix pattern.

### 8. False Positive Detection Workflow

**Score:** 4/10 (Cross-cutting +2, Repeated pattern +2)
**Trigger:** When automated review bot flags code changes
**Warning:** Verify the issue exists before changing code. Read context, check sibling implementations, reference project conventions.
**Target doc:** `docs/learned/review/tripwires.md`

Bots generate false positives regularly. This tripwire prevents blindly accepting suggestions.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Fake Service Filtering Implementation

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** May become HIGH if more fakes need filtering logic. Currently a testing-specific pattern.

### 2. Line Range References in Documentation

**Score:** 3/10 (Repeated pattern +2, Silent failure +1)
**Notes:** Could add automated CI check to catch line number patterns. Low frequency but high staleness risk.

### 3. Exception Analysis Workflow

**Score:** 2/10 (Repeated pattern +2)
**Notes:** Useful methodology but not critical enough for tripwire. Best documented as a pattern.

### 4. Prettier Formatting After Table Edits

**Score:** 2/10 (Silent failure +2)
**Notes:** CI catches this eventually. Tripwire would save iteration time but low severity.
