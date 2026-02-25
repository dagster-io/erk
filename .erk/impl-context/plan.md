# Documentation Plan: Add HTTP-accelerated path for Plans tab list refresh

## Context

This implementation introduced an HTTP-accelerated path for the Plans tab list refresh in the erk TUI. The work involved adding new gateway methods to the `HttpClient` ABC (`get_list()`, `graphql()`, and `supports_direct_api`), extracting pure parsing functions into a reusable module (`pr_data_parsing.py`), and threading an optional `http_client` parameter through the service layer. Four sessions contributed to this PR: planning (f3273e62), core implementation (882e2bf6), PR feedback addressing (impl-6052fbe3), and feedback classification (3f396ee2).

The implementation demonstrates several cross-cutting patterns that warrant documentation: the 5-place gateway ABC extension pattern, the no-default-parameters rule impacting 24+ call sites, time abstraction violations caught during PR review, and effective subagent delegation for mechanical refactoring. PR review threads (26 automated, 1 manual) provided concrete opportunities to strengthen type safety (TypedDict, Literal types) and consolidate error handling patterns.

Future agents working on gateway extensions, service ABC changes, or HTTP-based optimizations will benefit from documented tripwires and patterns from this implementation. The sessions also captured prevention insights around test coverage during function extraction and command discovery workflows.

## Raw Materials

PR #8193

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 26    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 8     |
| Potential tripwires (score2-3) | 6     |

## Documentation Items

### HIGH Priority

#### 1. Time Abstraction Violations

**Location:** `docs/learned/universal-tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session impl-6052fbe3 (5 violations), PR #8193 automated review

**Draft Content:**

```markdown
### Time Gateway Usage

**Trigger:** Before using `time.monotonic()`, `time.time()`, or `datetime.now()`

**Warning:** When Time gateway is injected (self._time), NEVER use time module directly. Always use `self._time.monotonic()` or `self._time.time()`. Direct time module usage breaks testability - cannot control time in tests without gateway abstraction.

See `src/erk/core/services/plan_list_service.py` for correct usage pattern with `self._time.monotonic()`.
```

---

#### 2. HttpClient ABC Extensions - 5-Place Implementation

**Location:** `docs/learned/gateway/tripwires.md`
**Action:** CREATE
**Source:** [Impl] CodeDiffAnalyzer inventory, Sessions 882e2bf6/f3273e62

**Draft Content:**

```markdown
# Gateway Tripwires

## HttpClient ABC Extensions

**Trigger:** Before adding methods or properties to HttpClient ABC

**Warning:** ALL 5 implementations must be updated:
1. `abc.py` - abstract method signature
2. `real.py` - actual HTTP implementation via httpx
3. `fake.py` - test double with response tracking
4. `dry_run.py` - no-op stub with logging
5. `printing.py` - delegation to wrapped client

See `packages/erk-shared/src/erk_shared/gateway/http/` - grep for method name in each file to verify all implementations exist.

## GraphQL Method Patterns

**Trigger:** Before adding GraphQL methods to HttpClient ABC

**Warning:** Same 5-place pattern as other methods. GraphQL-specific: sends POST to `/graphql` endpoint with `{"query": ..., "variables": ...}` payload. All 5 implementations need proper error handling and response parsing.

See `packages/erk-shared/src/erk_shared/gateway/http/real.py` for `graphql()` implementation pattern.
```

---

#### 3. Service ABC Parameter Threading

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] CodeDiffAnalyzer inventory, Session f3273e62

**Draft Content:**

```markdown
### Service ABC Parameter Changes

**Trigger:** Before adding parameters to service ABCs

**Warning:** ALL implementations must be updated:
1. ABC signature in `packages/erk-shared/src/erk_shared/core/`
2. Real implementations in `src/erk/core/services/`
3. Fake implementation in `packages/erk-shared/src/erk_shared/core/fakes.py`

Grep for the method name to find all locations. Parameter changes affect multiple files across packages.

This pattern demonstrated in PR #8193: `PlanListService.get_plan_list_data()` gained `http_client` parameter affecting 3+ implementation files.
```

---

#### 4. Default Parameters in ABC Signatures

**Location:** `docs/learned/dignified-python/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 882e2bf6 (24 call sites updated), PR #8193 automated review (4+ locations flagged)

**Draft Content:**

```markdown
### No Default Parameters - Reinforced

**Trigger:** Before adding optional parameters to ABCs or implementations

**Warning:** ABC signatures and implementations MUST NOT have default values, even for optional parameters like `http_client: HttpClient | None`. Remove default from signature, add explicit `None` at all call sites.

Impact when adding new optional param:
- ABC signature: remove `= None`
- All implementations: remove `= None`
- All call sites: add explicit `http_client=None` (may affect 20+ locations)

Forces explicit decisions and prevents hidden complexity. Consistent with LBYL philosophy.

See PR #8193 where 24 call sites were updated to explicitly pass `http_client=None`.
```

---

#### 5. Test Coverage After Function Extraction

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 882e2bf6 (AttributeError: `_merge_rest_graphql_pr_data` not found)

**Draft Content:**

```markdown
### Function Extraction Coverage

**Trigger:** Before extracting methods to standalone modules

**Warning:** Grep for all references (including in tests) BEFORE extracting. Update imports simultaneously. Failure to do so causes AttributeError at test time when old method name is still referenced.

Pattern:
1. Grep for method name: `grep -r "method_name" tests/`
2. List all files to update
3. Extract method AND update all imports in same commit
4. Run tests before committing

Discovered in PR #8193 when extracting `_merge_rest_graphql_pr_data` to `pr_data_parsing.py`.
```

---

#### 6. HTTP-Accelerated Plan Refresh Architecture

**Location:** `docs/learned/architecture/http-accelerated-plan-refresh.md`
**Action:** CREATE
**Source:** [Plan] Session f3273e62, [Impl] Session 882e2bf6

**Draft Content:**

```markdown
# HTTP-Accelerated Plan Refresh

## Overview

The Plans tab TUI supports two data fetching paths:
- **HTTP path**: Direct REST/GraphQL API calls via HttpClient (faster)
- **Subprocess path**: Shell out to `gh` CLI (fallback)

## When to Use HTTP vs Subprocess

HTTP path is preferred when:
- Direct API access is available (not in test fakes)
- Performance is critical (saves ~600-900ms per refresh)
- Need fine-grained control over API calls

Subprocess path is used when:
- Running with test fakes that don't support direct API
- Debugging API issues (gh output is more verbose)

## Routing Decision

The routing happens via `supports_direct_api` property on HttpClient:
- `RealHttpClient`: returns True
- `FakeHttpClient`: returns False

See `src/erk/core/services/plan_list_service.py` for routing logic in `PlannedPRPlanListService`.

## Three-Step HTTP Flow

1. **REST issues list**: Fetch open issues with `erk-plan` label
2. **GraphQL PR enrichment**: Batch fetch PR details (status, reviews, mergeable)
3. **GraphQL workflow runs**: Fetch CI status for associated commits

See `_get_plan_list_data_http()` in `src/erk/core/services/plan_list_service.py`.

## Performance Characteristics

- HTTP path: ~1.5-1.8s total
- Subprocess path: ~2.4s total
- Savings: ~600-900ms per refresh cycle

## Cross-References

- `docs/learned/architecture/github-cli-limits.md` - REST API over gh CLI for large operations
- `docs/learned/architecture/fast-path-pattern.md` - skipping expensive operations
- `docs/learned/tui/plan-list-provider-pattern.md` - data provider architecture
```

---

#### 7. PR Data Parsing Extraction Pattern

**Location:** `docs/learned/architecture/pr-data-parsing-extraction.md`
**Action:** CREATE
**Source:** [Impl] CodeDiffAnalyzer inventory, Session 882e2bf6

**Draft Content:**

```markdown
# PR Data Parsing Extraction Pattern

## Why Extract Parsing Functions

When multiple code paths (subprocess, HTTP) need to parse the same data format, extract parsing logic into pure stateless functions. Benefits:
- Code reuse between data fetching mechanisms
- Easier testing (pure functions have no dependencies)
- Clear separation of concerns

## Pattern: Pure Stateless Functions

Parsing functions should:
- Accept structured data (dict, list) as input
- Return structured data (dataclass, TypedDict) as output
- Have no side effects
- Not depend on gateways or services

## Extracted Functions

The `pr_data_parsing.py` module contains:
- `parse_status_rollup()` - Extract CI status from GraphQL response
- `parse_mergeable_status()` - Parse merge conflict state
- `parse_review_thread_counts()` - Count review threads by resolution state
- `merge_rest_graphql_pr_data()` - Combine REST and GraphQL PR data
- `parse_workflow_runs_nodes_response()` - Extract workflow run status

See `packages/erk-shared/src/erk_shared/gateway/github/pr_data_parsing.py`.

## Test Strategy

Layer 4 business logic tests for pure functions:
- Test each parsing function in isolation
- Use real API response fixtures
- No mocking required

See `tests/core/test_pr_data_parsing.py`.
```

---

#### 8. Dual-Path Collapse Checklist

**Location:** `docs/learned/architecture/dual-path-elimination.md`
**Action:** CREATE
**Source:** [Plan] Session f3273e62

**Draft Content:**

```markdown
# Dual-Path Elimination Refactoring

## Pattern Lifecycle

1. **Introduction**: Optional parameter + fallback path for gradual adoption
2. **Adoption complete**: All production code uses new path
3. **Elimination**: Remove optional marker, delete fallback, thread requirement

## Checklist When Collapsing Optional[Gateway] to Required

Before eliminating dual-path:

1. **Routing conditionals**: Search for `if gateway is not None` in callers
2. **Feature detection properties**: Check for `supports_X` or `can_do_Y` on gateway
3. **Subprocess fallback methods**: Find and delete `_method_subprocess()` variants
4. **Test suite overlap**: Identify tests covering both paths separately

## Threading Required Parameters

When making optional parameter required:

1. Remove `= None` from signature (ABC + all implementations)
2. Search for `param=None` at call sites - replace with real instance
3. Delete `if param is not None` routing conditionals
4. Update tests that explicitly passed `None`

## Pragmatic Tech Debt

When refactoring code scheduled for deletion:
- Accept unused parameters rather than porting functionality
- Document the decision in code comments
- Avoid over-engineering transitional code

See PR #8193 where `RealPlanListService` accepted `http_client` but didn't use it.
```

---

### MEDIUM Priority

#### 9. Subagent Clarification Loop Prevention

**Location:** `docs/learned/planning/subagent-prompting-patterns.md`
**Action:** CREATE
**Source:** [Impl] Session 3f396ee2 (subagent asked questions instead of executing)

**Draft Content:**

```markdown
# Subagent Prompting Patterns

## Problem: Clarification Loops

When launching Task tool with skill instructions, subagents may enter clarification mode and ask questions instead of executing.

## Insufficient Pattern

```
Load and follow the skill instructions in [path].
Return the complete JSON output as your final message.
```

This can trigger: "What PR number should I use? Should I include resolved threads?"

## Required Pattern

```
Load and follow the skill instructions in [path].
Execute the skill for the current branch and do NOT include resolved threads.
Return the complete JSON output as your final message.
Do NOT ask clarifying questions - proceed with the information available.
```

## Key Additions

1. **Explicit parameters**: Provide all inputs the skill needs
2. **Negative constraints**: "Do NOT ask questions"
3. **Imperative verbs**: "Execute", "Return", "Proceed"

See Session 3f396ee2 where first Task launch asked questions, second succeeded with explicit instructions.
```

---

#### 10. Libcst Delegation for Mechanical Changes

**Location:** `docs/learned/refactoring/libcst-delegation.md`
**Action:** CREATE
**Source:** [Impl] Session 882e2bf6 (20+ test calls needed `http_client=None`)

**Draft Content:**

```markdown
# Libcst Delegation for Mechanical Refactoring

## When to Delegate

Threshold: 15+ identical mechanical edits

Examples:
- Adding parameter to all function calls
- Renaming symbol across files
- Converting all `dict[str, Any]` to specific TypedDict

## How to Delegate

Launch `libcst-refactor` subagent with clear prompt:

```
Add `http_client=None` to all calls to `get_plan_list_data()` in tests/*.
Do not change any other code.
Report files modified when complete.
```

## Benefits

- Reduces manual edit errors
- Consistent formatting
- Faster for large-scale changes

## When NOT to Delegate

- Fewer than 15 edits (faster to do manually)
- Complex context-dependent changes
- Changes requiring judgment per-instance

See Session 882e2bf6 where 20+ test call sites were updated via libcst delegation.
```

---

#### 11. HTTP Request Helper Extraction

**Location:** `docs/learned/refactoring/http-error-handling-consolidation.md`
**Action:** CREATE
**Source:** [Impl] CodeDiffAnalyzer inventory (RealHttpClient refactor), PR #8193 automated review

**Draft Content:**

```markdown
# HTTP Error Handling Consolidation

## Pattern Recognition

When HTTP methods repeat this pattern:
1. Build URL from base + endpoint
2. Make request with headers/timeout
3. Check status >= 400
4. Raise HttpError if failed
5. Return response.json()

## Solution: `_make_request()` Helper

Extract common logic into private helper:

```python
def _make_request(self, method: str, endpoint: str, ...) -> dict:
    url = f"{self._base_url}{endpoint}"
    response = self._client.request(method, url, ...)
    if response.status_code >= 400:
        raise HttpError(response.status_code, response.text)
    return response.json()
```

Then simplify public methods:
```python
def get(self, endpoint: str) -> dict:
    return self._make_request("GET", endpoint)
```

## Applies To

- `RealHttpClient`: actual HTTP implementation
- `FakeHttpClient`: test double (extract `_get_response()` helper)

See `packages/erk-shared/src/erk_shared/gateway/http/real.py` for `_make_request()` pattern.
```

---

#### 12. Gateway Feature Detection Anti-Pattern

**Location:** `docs/learned/architecture/gateway-feature-detection.md`
**Action:** CREATE
**Source:** [Plan] Session f3273e62 (`supports_direct_api` had single caller)

**Draft Content:**

```markdown
# Gateway Feature Detection Properties

## Anti-Pattern: Single-Caller Feature Detection

Red flag: `supports_X` or `can_do_Y` property with only one caller.

Example:
```python
# In HttpClient ABC
@property
def supports_direct_api(self) -> bool: ...

# Single caller in routing logic
if http_client.supports_direct_api:
    return self._get_data_http()
else:
    return self._get_data_subprocess()
```

## Why It's a Code Smell

- Adds abstraction without reuse benefit
- Property exists solely for one conditional
- When routing logic is eliminated, property becomes dead code

## Resolution

When eliminating dual-path routing:
1. Delete the `supports_X` property from ABC
2. Delete all implementations
3. Delete the routing conditional

## When Feature Detection IS Appropriate

- Multiple callers need the capability check
- Capability varies meaningfully across implementations
- Used for logging/telemetry, not routing

See PR #8193 where `supports_direct_api` was identified for removal during dual-path elimination planning.
```

---

#### 13. GraphQL Schema Mismatch Fallback

**Location:** `docs/learned/integrations/github-graphql-fallback.md`
**Action:** CREATE
**Source:** [Impl] Session impl-6052fbe3 (`pullRequestReviewThreadId` not accepted in mutation)

**Draft Content:**

```markdown
# GitHub GraphQL Schema Fallback

## Problem

GraphQL mutations may fail with: "InputObject 'X' doesn't accept argument 'Y'"

This happens when:
- Schema has changed
- Documentation is outdated
- Field exists in query but not mutation input

## Example

Attempted:
```graphql
mutation {
  addPullRequestReviewComment(input: {
    pullRequestReviewThreadId: "..."  # FAILS
  })
}
```

Error: `InputObject 'AddPullRequestReviewCommentInput' doesn't accept argument 'pullRequestReviewThreadId'`

## Solution: REST API Fallback

REST APIs often provide equivalent functionality with different parameter names:

```bash
gh api repos/{owner}/{repo}/pulls/comments/{id}/replies \
  -f body="Reply text"
```

The REST endpoint uses `in_reply_to_id` (implicit in URL) instead of `pullRequestReviewThreadId`.

## General Pattern

1. Try GraphQL mutation
2. If schema error, search for REST API equivalent
3. REST parameters may have different names for same concept

See Session impl-6052fbe3 for complete PR thread resolution workflow.
```

---

#### 14. Type Strengthening Patterns

**Location:** `docs/learned/dignified-python/references/type-hints.md`
**Action:** UPDATE
**Source:** [Impl] PR #8193 review comments, CodeDiffAnalyzer (MergeableStatus, StatusCheckRollupData)

**Draft Content:**

```markdown
## Type Strengthening at API Boundaries

### Literal for Known String Values

When a parameter accepts only specific string values from an external API:

```python
# Before
def parse_mergeable(status: str) -> ...: ...

# After
MergeableStatus = Literal["MERGEABLE", "CONFLICTING", "UNKNOWN"]
def parse_mergeable(status: MergeableStatus) -> ...: ...
```

Benefits:
- Compile-time validation
- IDE autocomplete
- Self-documenting API

### TypedDict for Structured API Responses

When parsing external API responses with known structure:

```python
# Before
def parse_rollup(data: dict[str, Any]) -> ...: ...

# After
class StatusCheckRollupData(TypedDict):
    state: str
    contexts: dict[str, Any]

def parse_rollup(data: StatusCheckRollupData) -> ...: ...
```

See `packages/erk-shared/src/erk_shared/gateway/github/types.py` for examples.
```

---

#### 15. Dictionary Mapping Over If/Elif Chains

**Location:** `docs/learned/dignified-python/references/clarity.md`
**Action:** CREATE
**Source:** [Impl] Session 882e2bf6 (status/conclusion mapping refactor), PR #8193 automated review

**Draft Content:**

```markdown
# Clarity Patterns

## Dictionary Mapping Over If/Elif Chains

### When to Use

When mapping known values to other values with 3+ branches:

```python
# Before (verbose)
if status == "queued":
    return "PENDING"
elif status == "in_progress":
    return "PENDING"
elif status == "completed":
    return conclusion_map[conclusion]
else:
    return "UNKNOWN"

# After (clear)
status_map = {
    "queued": "PENDING",
    "in_progress": "PENDING",
    "completed": None,  # Use conclusion
}
return status_map.get(status, "UNKNOWN") or conclusion_map.get(conclusion, "UNKNOWN")
```

### Benefits

- More maintainable
- Easier to extend (add new key)
- Reduces indentation
- Makes mapping explicit

### When NOT to Use

- Complex conditional logic (not pure value mapping)
- Side effects needed per branch
- Fewer than 3 branches
```

---

#### 16. Batch PR Review Workflow

**Location:** `docs/learned/pr-operations/batch-review-workflow.md`
**Action:** UPDATE
**Source:** [Impl] Session 882e2bf6 (24 threads -> 2 batches), Session impl-6052fbe3 (REST API for replies)

**Draft Content:**

```markdown
## End-to-End Batch Review Workflow

### Step 1: Classify Feedback

Use `pr-feedback-classifier` skill via Task tool:

```
Execute the pr-feedback-classifier skill for PR #123.
Do NOT include resolved threads.
Return the complete JSON output.
```

### Step 2: Batch by Complexity

Typical batches:
- **Batch 1 - Local Fixes**: Single-line changes, typos, formatting
- **Batch 2 - Single-File Changes**: Test additions, refactors within one file

### Step 3: Address Systematically

1. Fix all items in batch
2. Commit with descriptive message
3. Resolve threads with commit SHA reference

### Step 4: Resolve Threads

Two-step process:

1. **Reply to comment** (REST API):
```bash
gh api repos/{owner}/{repo}/pulls/comments/{comment_id}/replies \
  -f body="Fixed in commit abc123"
```

2. **Resolve thread** (erk exec):
```bash
echo '[{"thread_id": "PRRT_..."}]' | erk exec resolve-review-threads
```

### Step 5: Verify Completion

Re-run classifier to confirm all actionable threads resolved.

See Session 882e2bf6 for example handling 24 threads in 2 batches.
```

---

### LOW Priority

#### 17. Test Suite Consolidation

**Location:** `docs/learned/testing/test-suite-consolidation.md`
**Action:** CREATE
**Source:** [Plan] Session f3273e62

**Draft Content:**

```markdown
# Test Suite Consolidation

## When to Consolidate

When dual-path implementation has separate test suites for each path:
- `test_service.py` - tests subprocess path
- `test_service_http.py` - tests HTTP path

## Decision Framework

1. **Check coverage overlap**: Do both suites test same business logic?
2. **Assess path permanence**: Is one path being deleted?
3. **Compare test quality**: Which suite has better edge case coverage?

## Action: Delete vs Convert

**Delete** subprocess path tests when:
- HTTP tests already cover same functionality
- Subprocess path is being removed

**Convert** to HTTP tests when:
- Subprocess tests cover unique edge cases
- HTTP tests are missing coverage

## Anti-Pattern: Mechanical Conversion

Don't automatically convert all subprocess tests to FakeHttpClient. If HTTP tests already exist, the conversion creates redundant tests.

See PR #8193 where `TestPlannedPRPlanListService` was recommended for deletion rather than conversion.
```

---

#### 18. Pragmatic Tech Debt Acceptance

**Location:** `docs/learned/refactoring/pragmatic-tech-debt.md`
**Action:** CREATE
**Source:** [Plan] Session f3273e62 (RealPlanListService accepts http_client but doesn't use it)

**Draft Content:**

```markdown
# Pragmatic Tech Debt Acceptance

## Context

When refactoring touches code scheduled for deletion, avoid over-engineering.

## Pattern

Accept unused parameters in transitional code rather than:
- Porting full functionality to the new interface
- Creating elaborate adapters
- Extensive test coverage for soon-deleted code

## Example

`RealPlanListService` accepted `http_client` parameter but didn't use it:
```python
def get_plan_list_data(self, http_client: HttpClient) -> PlanListData:
    # http_client unused - this service queries via GitHubIssues gateway
    # Acceptable because RealPlanListService is scheduled for deletion
    return self._fetch_via_issues_gateway()
```

## Decision Criteria

- Code is scheduled for deletion (roadmap item, tech debt ticket)
- Porting functionality would take significant effort
- The unused parameter doesn't break anything

## Document the Decision

Add code comment explaining why parameter is unused and when it will be removed.
```

---

#### 19. Command Discovery Workflow

**Location:** `docs/learned/cli/command-discovery.md`
**Action:** CREATE
**Source:** [Impl] Session impl-6052fbe3 (tried `erk exec pr-thread reply` which doesn't exist)

**Draft Content:**

```markdown
# Command Discovery Workflow

## Problem

Guessing command names leads to errors:
```bash
erk exec pr-thread reply  # Doesn't exist!
```

## Solution: Check Before Using

### Option 1: List and Grep

```bash
erk exec -h | grep -i thread
```

### Option 2: Search Codebase

```bash
grep -r "thread" src/erk/cli/commands/exec/
```

### Option 3: Read Help Text

```bash
erk exec resolve-review-threads -h
```

## Common Mistake

Assuming command structure matches mental model. The actual command may be:
- Different subcommand group
- Different verb
- Expects different input format

Always verify before using.
```

---

#### 20. CLI Input Format Verification

**Location:** `docs/learned/cli/cli-input-formats.md`
**Action:** CREATE
**Source:** [Impl] Session impl-6052fbe3 (passed `--thread-ids` flag to command expecting JSON stdin)

**Draft Content:**

```markdown
# CLI Input Format Verification

## Problem

Commands may expect different input formats than assumed:

```bash
# Assumed: CLI flags
erk exec resolve-review-threads --thread-ids ID1 ID2

# Actual: JSON stdin
echo '[{"thread_id": "ID1"}]' | erk exec resolve-review-threads
```

## Solution

Read command help before using:

```bash
erk exec resolve-review-threads -h
```

Look for:
- `--flag` options (CLI arguments)
- "stdin" or "JSON" mentions (piped input)
- "positional" arguments (after command)

## Common Patterns in erk

- Batch operations: JSON stdin
- Single-item operations: CLI flags
- Interactive operations: prompts

Always verify the expected format to avoid silent failures.
```

---

#### 21. Variable Proximity Pattern

**Location:** `docs/learned/dignified-python/references/clarity.md`
**Action:** UPDATE
**Source:** [Impl] PR #8193 automated review (flagged intermediate variables)

**Draft Content:**

```markdown
## Variable Proximity

### Rule

Declare variables close to use. If used once in constructor, inline directly.

### Anti-Pattern

```python
# Extracting single-use variable far from use
label_names = ["erk-plan", "erk-learn"]
# ... 20 lines later ...
service = PlanListService(labels=label_names)
```

### Correct Pattern

```python
# Inline single-use values
service = PlanListService(labels=["erk-plan", "erk-learn"])
```

### When to Extract

- Value used multiple times
- Complex expression that benefits from naming
- Improves readability significantly

### When to Inline

- Used exactly once
- Simple value (list literal, string)
- Distance to use is small
```

---

#### 22. Consistent Error Handling in Fakes

**Location:** `docs/learned/testing/fake-patterns.md`
**Action:** UPDATE
**Source:** [Impl] PR #8193 automated review (get_list() duplicating error checking)

**Draft Content:**

```markdown
## Consistent Error Handling

### Pattern

Extract common error handling to helpers in fake implementations:

```python
class FakeHttpClient:
    def _get_response(self, url: str) -> dict:
        if url not in self._responses:
            raise HttpError(404, f"No response configured for {url}")
        return self._responses[url]

    def get(self, endpoint: str) -> dict:
        return self._get_response(endpoint)

    def get_list(self, endpoint: str) -> list[dict]:
        return self._get_list_response(endpoint)
```

### Benefits

- Consistent behavior across all methods
- Single place to update error handling
- Easier to add new methods

See `packages/erk-shared/src/erk_shared/gateway/http/fake.py` for implementation.
```

---

#### 23. FakeHttpClient.set_list_response()

**Location:** `docs/learned/testing/fake-patterns.md`
**Action:** UPDATE
**Source:** [Impl] CodeDiffAnalyzer inventory

**Draft Content:**

```markdown
## List Response Configuration

When testing endpoints that return lists:

```python
fake_http = FakeHttpClient()

# For single dict responses
fake_http.set_response("/issues/123", {"id": 123, "title": "Test"})

# For list responses
fake_http.set_list_response("/issues", [
    {"id": 1, "title": "Issue 1"},
    {"id": 2, "title": "Issue 2"},
])
```

Methods:
- `set_response()` - returns `dict`
- `set_list_response()` - returns `list[dict]`

See `packages/erk-shared/src/erk_shared/gateway/http/fake.py`.
```

---

#### 24. Multi-Layer Test Coverage Strategy

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl] Session 882e2bf6 (47 tests across 4 layers)

**Draft Content:**

```markdown
## Multi-Layer Test Coverage

When adding modules with multiple components, use layered testing:

### Layer 4 - Business Logic Tests

Pure function tests for stateless parsing/transformation:
- Location: `tests/core/`
- No mocking required
- Fast, deterministic

Example: `test_pr_data_parsing.py` (24 tests)

### Layer 3 - Fake Tests

Validate fake implementations behave correctly:
- Location: `tests/unit/fakes/`
- Test fake configuration and responses

Example: `test_fake_http_client.py` (7 tests)

### Layer 2 - Real Tests

Test real implementations with mocked boundaries:
- Location: `tests/real/`
- Mock external dependencies (httpx, subprocess)

Example: `test_real_http_client.py` (9 tests)

### Layer 4 - Integration Tests

End-to-end tests with fake dependencies:
- Location: `tests/unit/services/`
- Real service code, fake gateways

Example: `test_plan_list_service_http.py` (6 tests)

See PR #8193 for comprehensive example across all layers.
```

---

#### 25. Rebase Conflicts on Parameter Additions

**Location:** `docs/learned/refactoring/optional-parameter-conflicts.md`
**Action:** CREATE
**Source:** [Impl] Session 882e2bf6 (rebase conflict on http_client parameter)

**Draft Content:**

```markdown
# Rebase Conflicts on Parameter Additions

## Pattern

When adding optional parameters to function calls, expect rebase conflicts.

## Why Conflicts Occur

- **Base branch**: `service.get_data()`
- **Your branch**: `service.get_data(http_client=http)`
- **Conflict**: Both change same line

## Resolution Strategy

Keep incoming parameter additions:

```python
<<<<<<< HEAD
result = service.get_data()
=======
result = service.get_data(http_client=http_for_service)
>>>>>>> your-branch
```

Resolve to:
```python
result = service.get_data(http_client=http_for_service)
```

## Prevention

When working on branches that add parameters:
- Rebase frequently to catch conflicts early
- Coordinate with team on call site changes
- Consider feature flags for gradual rollout
```

---

#### 26. SHOULD_BE_CODE Items

**Location:** Various source files (docstrings)
**Action:** CODE_CHANGE
**Source:** [Impl] CodeDiffAnalyzer inventory

These items should have docstrings added to the source code rather than learned docs:

1. **`parse_status_rollup()`** - Add docstring explaining input/output transformation
2. **`parse_mergeable_status()`** - Add docstring for mergeable state parsing
3. **`parse_review_thread_counts()`** - Add docstring for thread counting logic
4. **`merge_rest_graphql_pr_data()`** - Add docstring for data merging strategy
5. **`parse_workflow_runs_nodes_response()`** - Add docstring for workflow parsing

Location: `packages/erk-shared/src/erk_shared/gateway/github/pr_data_parsing.py`

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Time Abstraction Violations

**What happened:** 5 instances of `time.monotonic()` used directly instead of `self._time.monotonic()` when Time gateway was available.

**Root cause:** Muscle memory from standard Python patterns. Easy to forget gateway abstraction exists.

**Prevention:** Tripwire in universal-tripwires.md. Before using time module, check if Time gateway is injected.

**Recommendation:** TRIPWIRE (Score: 6)

### 2. Test Import Failures After Extraction

**What happened:** Tests failed with `AttributeError: 'RealGitHub' object has no attribute '_merge_rest_graphql_pr_data'` after extracting method to module.

**Root cause:** Extracted method without updating test imports simultaneously.

**Prevention:** Grep for all references before extracting. Update imports in same commit.

**Recommendation:** TRIPWIRE (Score: 5)

### 3. Subagent Clarification Loops

**What happened:** Task tool subagent asked clarifying questions instead of executing skill.

**Root cause:** Prompt was insufficiently explicit. "Load and follow skill" triggered planning mode.

**Prevention:** Add explicit imperatives: "Execute [action]. Do NOT ask questions. Return [output]."

**Recommendation:** ADD_TO_DOC (Score: 3)

### 4. Command Name Guessing

**What happened:** Tried `erk exec pr-thread reply` which doesn't exist.

**Root cause:** Assumed command structure without verification.

**Prevention:** Use `erk exec -h | grep -i keyword` before using unknown commands.

**Recommendation:** ADD_TO_DOC (Score: 2)

### 5. CLI Input Format Mismatch

**What happened:** Passed `--thread-ids` flag to command expecting JSON stdin.

**Root cause:** Didn't read command help to understand input format.

**Prevention:** Always read `-h` output before using unfamiliar commands.

**Recommendation:** ADD_TO_DOC (Score: 2)

### 6. GraphQL Schema Assumptions

**What happened:** GraphQL mutation rejected `pullRequestReviewThreadId` parameter.

**Root cause:** Assumed GraphQL schema matched documentation/intuition.

**Prevention:** When GraphQL fails with schema errors, fall back to REST API.

**Recommendation:** ADD_TO_DOC (Score: 3)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Time Abstraction Violations

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before using `time.monotonic()`, `time.time()`, or `datetime.now()`
**Warning:** When Time gateway is injected (self._time), NEVER use time module directly. Always use self._time.monotonic() / self._time.time(). Breaks testability.
**Target doc:** `docs/learned/universal-tripwires.md`

This is tripwire-worthy because the violation is invisible at runtime but causes test flakiness. Five instances were caught in PR review, indicating agents repeatedly make this mistake. The warning should appear before any time-related imports or calls.

### 2. HttpClient ABC Extensions - 5-Place Implementation

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before adding methods or properties to HttpClient ABC
**Warning:** ALL 5 implementations must be updated: abc.py, real.py, fake.py, dry_run.py, printing.py
**Target doc:** `docs/learned/gateway/tripwires.md`

Missing any implementation causes runtime errors. The pattern is not obvious from looking at a single file. This PR added 3 new members requiring 15 implementation updates total.

### 3. HttpClient GraphQL Methods

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before adding GraphQL methods to HttpClient ABC
**Warning:** Same 5-place pattern. GraphQL-specific: POST to /graphql with {query, variables} payload.
**Target doc:** `docs/learned/gateway/tripwires.md`

GraphQL methods have additional complexity beyond regular HTTP methods. The POST-with-body pattern differs from REST conventions.

### 4. Test Coverage After Function Extraction

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before extracting methods to standalone modules
**Warning:** Grep for all references (including tests) first. Update imports simultaneously.
**Target doc:** `docs/learned/testing/tripwires.md`

AttributeError at test time is confusing. The extraction appears successful until tests run. Grep-first prevents this.

### 5. Default Parameters in ABC Signatures

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before adding optional parameters to ABCs or implementations
**Warning:** Remove defaults from signatures. Add explicit values at all call sites (may be 20+ locations).
**Target doc:** `docs/learned/dignified-python/tripwires.md`

Automated review flagged 4+ locations. The pattern is well-documented but still violated. Reinforcement via tripwire helps.

### 6. Service ABC Parameter Threading

**Score:** 4/10 (Cross-cutting +2, Destructive potential +2)
**Trigger:** Before adding parameters to service ABCs
**Warning:** ALL implementations must be updated: ABC, real implementations, fake implementation.
**Target doc:** `docs/learned/architecture/tripwires.md`

Missing any implementation causes runtime errors. The files are spread across packages, making it easy to miss one.

### 7. Dual-Path Collapse Checklist

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When collapsing Optional[Gateway] to required Gateway
**Warning:** Check for routing conditionals, feature detection properties, subprocess fallbacks, test overlap.
**Target doc:** `docs/learned/architecture/tripwires.md`

Complex refactoring with multiple considerations. Easy to miss one aspect and leave dead code.

### 8. Gateway Feature Detection Single-Caller

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When adding supports_X or can_do_Y properties to gateways
**Warning:** Single-caller feature detection is a code smell. Eliminate property when eliminating routing logic.
**Target doc:** `docs/learned/architecture/tripwires.md`

Prevents unnecessary abstraction. Properties should serve multiple callers to justify their existence.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Subagent Clarification Loops

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Task tool with skills needs explicit instructions. Pattern documented in subagent-prompting-patterns.md. May warrant tripwire if more incidents occur.

### 2. Libcst Delegation Threshold

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** 15+ identical edits suggest libcst delegation. Pattern documented in refactoring/libcst-delegation.md. Not critical enough for tripwire.

### 3. HTTP Request Helper Extraction

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** DRY pattern for HTTP methods. More of a code quality improvement than error prevention.

### 4. Dual-Path Elimination Checklist

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Already covered by "Dual-Path Collapse Checklist" tripwire candidate. This is the detailed checklist, tripwire is the trigger.

### 5. Gateway Feature Detection Code Smell

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Promoted to score-4 tripwire candidate. Single-caller properties warrant warning.

### 6. GraphQL Schema Fallback

**Score:** 3/10 (External tool quirk +1, Non-obvious +2)
**Notes:** GitHub-specific issue. Documented in integrations/github-graphql-fallback.md. Not frequent enough for tripwire.
