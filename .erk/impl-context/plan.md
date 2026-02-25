# Documentation Plan: Add targeted plan fetching by issue number for objective plans modal

## Context

This implementation addressed a visibility problem in the ObjectivePlansScreen modal: with 3,538+ closed erk-plan issues, the previous limit=200 list query approach missed most closed plans, causing the modal to show incomplete data (e.g., 1 plan visible when 6 were referenced in the objective's roadmap). The solution introduced targeted plan fetching by extracting plan IDs from objective roadmap metadata and fetching only those specific issues via batched GraphQL queries.

The implementation demonstrated excellent execution of erk's core patterns: the 5-place gateway ABC implementation (ABC -> Real -> Fake -> DryRun -> Printing), GraphQL union type handling with `issueOrPullRequest`, and the architectural principle of preferring targeted fetching over broad queries with client-side filtering. Future agents would benefit from documentation of these patterns, particularly the non-obvious GraphQL behavior around issues vs merged PRs.

Key insights from this implementation include: (1) the `issueOrPullRequest(number: N)` GraphQL field is required when plan issues could be either GitHub issues or merged PRs, (2) batched alias queries enable efficient multi-item fetches in a single GraphQL call, and (3) roadmap metadata provides explicit plan IDs that eliminate the need for broad queries and pagination limits.

## Raw Materials

Associated with PR #8163

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 16    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 5     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Gateway ABC 5-place implementation tripwire reinforcement

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8163]

**Draft Content:**

```markdown
## Gateway Method Implementation Pattern

When adding a new gateway method, implementation is required across multiple locations depending on the gateway type:

**GitHub Gateway (5-place pattern):**
1. ABC abstract method signature
2. Real implementation with actual API logic
3. Fake implementation returning filtered test data
4. DryRun wrapper delegating to wrapped for reads
5. Printing wrapper delegating with optional logging

**PlanDataProvider Gateway (3-place pattern):**
1. ABC abstract method signature
2. Real implementation
3. Fake implementation

See `packages/erk-shared/src/erk_shared/gateway/github/` for implementation examples. The `get_issues_by_numbers_with_pr_linkages()` method demonstrates the complete 5-place pattern.

**Tripwire:** Before adding a new gateway method, verify you have identified ALL required implementation locations. Incomplete implementations cause runtime failures in specific modes (test, dry-run, printing).
```

---

#### 2. GraphQL issueOrPullRequest tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8163]

**Draft Content:**

```markdown
## GitHub GraphQL: issueOrPullRequest vs issue

When fetching GitHub items by number that could be either issues OR merged pull requests, use `issueOrPullRequest(number: N)` not `issue(number: N)`.

**Why this matters:** Some erk-plan issues are merged PRs, not issues. Using `issue(number: N)` returns null for merged PRs, causing silent data loss.

**Pattern:** Batched alias queries enable fetching multiple items efficiently:

```graphql
repository(owner: "...", name: "...") {
  issue_8070: issueOrPullRequest(number: 8070) { ...fields }
  issue_8071: issueOrPullRequest(number: 8071) { ...fields }
}
```

**Tripwire:** Before fetching GitHub items by number, determine if the item could be a merged PR. If yes, use `issueOrPullRequest`.

See `packages/erk-shared/src/erk_shared/gateway/github/real.py` for implementation reference (`_build_issues_by_numbers_query`).
```

---

#### 3. GraphQL issueOrPullRequest pattern documentation

**Location:** `docs/learned/architecture/github-graphql-patterns.md`
**Action:** CREATE
**Source:** [Impl] [PR #8163]

**Draft Content:**

```markdown
---
read-when:
  - writing GraphQL queries for GitHub issues or PRs by number
  - fetching items that could be either issues or merged PRs
  - building batched GraphQL queries with aliases
category: architecture
---

# GitHub GraphQL: Issue vs PR Query Patterns

## The issueOrPullRequest Union Type

The `issueOrPullRequest(number: N)` field returns a union type that can be either an Issue or a PullRequest. This is essential when fetching items by number that may have been converted from issues to merged PRs.

## When to Use

Use `issueOrPullRequest` instead of `issue` when:
- Fetching erk-plan issues (some are merged draft PRs)
- Fetching items where the type is unknown at query time
- The item number may have been reassigned through PR merge

## Batched Alias Pattern

For fetching multiple items efficiently, use aliased queries:

```graphql
repository(owner: "...", name: "...") {
  item_100: issueOrPullRequest(number: 100) {
    ... on Issue { title body state number }
    ... on PullRequest { title body state number }
  }
  item_101: issueOrPullRequest(number: 101) {
    ... on Issue { title body state number }
    ... on PullRequest { title body state number }
  }
}
```

## Implementation Reference

See `packages/erk-shared/src/erk_shared/gateway/github/real.py`:
- Query building: `_build_issues_by_numbers_query()`
- Response parsing: `_parse_issues_by_numbers_response()`

## Body Field Consistency

Both Issue and PullRequest have a `body` field that returns markdown. Use `body` (not `bodyText`) to maintain format consistency.
```

---

#### 4. Targeted fetching pattern documentation

**Location:** `docs/learned/architecture/targeted-fetching.md`
**Action:** CREATE
**Source:** [Impl] [PR #8163]

**Draft Content:**

```markdown
---
read-when:
  - deciding between list queries vs targeted ID fetching
  - implementing features that display subsets of large datasets
  - extracting IDs from metadata for subsequent fetches
category: architecture
---

# Targeted Fetching Pattern

## Overview

When metadata contains explicit references (IDs, numbers), prefer extracting those references and fetching specific items rather than using broad list queries with client-side filtering.

## Pattern

1. **Extract IDs from metadata** (e.g., parse roadmap frontmatter for plan IDs)
2. **Fetch specific items by ID** (e.g., `fetch_plans_by_ids(plan_ids)`)
3. **Fall back to broad query** only when metadata is unavailable

## When to Apply

**Use targeted fetching when:**
- Metadata contains explicit item references (roadmap PRs, linked issues)
- The full dataset is large (thousands of items)
- List queries have pagination limits that may miss items

**Use broad queries when:**
- No explicit references exist in metadata
- Items need to be discovered by attributes (state, labels)
- The dataset is small enough for complete retrieval

## Benefits

- **Completeness:** No missed items due to pagination limits
- **Performance:** Fetch only what's needed
- **Accuracy:** Display exactly what metadata references

## Implementation Example

See `src/erk/tui/screens/objective_plans_screen.py`:
- `_extract_plan_ids_from_roadmap()` extracts IDs from roadmap metadata
- `_fetch_plans()` uses targeted fetch with fallback to broad query
```

---

#### 5. Testing methods with complex business logic tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8163]

**Draft Content:**

```markdown
## Test Complex Business Logic Methods

Methods with complex business logic require unit tests covering main paths and edge cases. This includes:

- **GraphQL query building:** Verify query structure, aliases, fragments
- **GraphQL response parsing:** Test single items, multiple items, null handling, empty responses
- **Multi-step orchestration:** Test each transformation step
- **Data extraction from structured formats:** Test extraction logic with various inputs

**Tripwire:** Before implementing methods that build GraphQL queries, parse responses, or orchestrate multi-step data transformations, plan the test cases covering: empty input, single item, multiple items, null/missing fields, and error conditions.

See `tests/unit/gateways/github/test_real.py` for examples: `test_build_issues_by_numbers_query_*` and `test_parse_issues_by_numbers_response_*`.
```

---

### MEDIUM Priority

#### 6. Roadmap metadata extraction pattern

**Location:** `docs/learned/tui/roadmap-extraction.md`
**Action:** CREATE
**Source:** [Impl] [PR #8163]

**Draft Content:**

```markdown
---
read-when:
  - extracting plan IDs from objective roadmap metadata
  - parsing roadmap frontmatter blocks
  - working with objective-related features in TUI
category: tui
---

# Roadmap Metadata Extraction

## Overview

Objective issue bodies contain roadmap metadata in YAML frontmatter blocks. The `parse_roadmap()` function from `erk_shared.gateway.github.metadata.roadmap` extracts structured data from these blocks.

## Extracting Plan IDs

Roadmap nodes contain PR references (e.g., `#8070`) that can be extracted to get plan IDs:

1. Call `parse_roadmap(objective_body)` to get roadmap structure
2. Iterate over roadmap nodes
3. Filter for nodes with non-null `pr` field
4. Strip `#` prefix and convert to int

## Implementation Reference

See `src/erk/tui/screens/objective_plans_screen.py` for the `_extract_plan_ids_from_roadmap()` helper function.

## Notes

- Null PRs should be skipped (planned but not yet created)
- Return as `set[int]` for natural deduplication
- Empty body or missing roadmap block returns empty set
```

---

#### 7. Batched alias GraphQL queries

**Location:** `docs/learned/architecture/github-graphql.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8163]

**Draft Content:**

```markdown
## Batched Alias Queries

When fetching multiple items by ID in a single GraphQL call, use aliased fields:

```graphql
repository(owner: "...", name: "...") {
  item_100: issueOrPullRequest(number: 100) { ...fields }
  item_101: issueOrPullRequest(number: 101) { ...fields }
}
```

**Why aliases:** GraphQL field names must be unique within a selection set. Aliases allow fetching multiple items of the same type with different arguments.

**Response parsing:** The response contains keys matching the aliases (`item_100`, `item_101`). Iterate over aliased keys to process results.

See `packages/erk-shared/src/erk_shared/gateway/github/real.py` for implementation.
```

---

#### 8. PlanDataProvider extension pattern

**Location:** `docs/learned/tui/data-contract.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8163]

**Draft Content:**

```markdown
## When to Add New PlanDataProvider Methods

Add a new method to PlanDataProvider when:
- An existing method fetches more data than needed (performance)
- Client-side filtering would be complex or lossy
- The new fetch pattern is reusable across multiple screens

**Case Study: fetch_plans_by_ids()**

Added `fetch_plans_by_ids(plan_ids: set[int])` instead of modifying `fetch_plans()` because:
- Targeted fetching by ID is fundamentally different from list queries
- No pagination limits when fetching by ID
- Enables roadmap-based fetching pattern

**Implementation checklist:**
1. ABC abstract method signature
2. Real implementation (calls underlying gateway, converts to PlanRowData)
3. Fake implementation (filters test data by matching IDs)

See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/` for implementation.
```

---

#### 9. ObjectivePlansScreen behavior

**Location:** `docs/learned/tui/objective-plans-screen.md`
**Action:** CREATE
**Source:** [Impl] [PR #8163]

**Draft Content:**

```markdown
---
read-when:
  - modifying ObjectivePlansScreen behavior
  - understanding objective plan fetching strategy
  - implementing new objective-related modals
category: tui
---

# ObjectivePlansScreen

## Overview

Modal screen displaying plans linked to an objective. Uses roadmap-based targeted fetching with fallback to broad query.

## Constructor Parameters

- `provider`: PlanDataProvider for data fetching
- `objective_issue`: Issue number of the objective
- `objective_body`: Full markdown body of the objective (used for roadmap extraction)

## Fetching Strategy

1. **Extract plan IDs from roadmap:** Parse `objective_body` for roadmap metadata
2. **Targeted fetch:** If plan IDs found, call `provider.fetch_plans_by_ids()`
3. **Fallback:** If no roadmap IDs, call `provider.fetch_plans_for_objective()`

## State Filter Change

`fetch_plans_for_objective()` now fetches plans with any state (not just open) to align with targeted fetching behavior.

## Implementation Reference

See `src/erk/tui/screens/objective_plans_screen.py` for full implementation.
```

---

#### 10. Large file navigation with persisted output

**Location:** `docs/learned/capabilities/persisted-output.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - reading large files that exceed context limits
  - Claude Code returns persisted output paths
  - navigating through tool-results files
category: capabilities
---

# Large File Navigation with Persisted Output

## Overview

When files exceed approximately 2KB, Claude Code saves them to `.claude/projects/.../tool-results/` and provides a preview plus full path.

## Navigation Pattern

1. **Initial read:** Claude Code provides preview and persisted path
2. **Incremental reading:** Use `offset` and `limit` parameters to navigate
3. **Targeted sections:** Use Grep to find line numbers, then Read with offset/limit

## Best Practices

- Don't re-read entire large files multiple times
- Use Grep to locate specific methods/sections
- Read in chunks using offset/limit (e.g., lines 680-980, then 1-100)
- Cache utilization: Heavy ephemeral cache reads indicate effective context reuse

## Example

```
# Find method location
Grep pattern="def my_method" path="large_file.py"

# Read specific section
Read file_path="large_file.py" offset=680 limit=100
```
```

---

#### 11. Plan file override workflow

**Location:** `docs/learned/planning/plan-save-workflow.md`
**Action:** CREATE
**Source:** [Plan]

**Draft Content:**

```markdown
---
read-when:
  - plan-save results in unexpected content
  - bypassing session plan mode content
  - saving arbitrary plan content without plan mode
category: planning
---

# Plan Save Workflow and Overrides

## Standard Workflow

`/erk:plan-save` reads from the session's plan mode file by default.

## The --plan-file Override

When plan mode content doesn't match intent, use `--plan-file` to specify content directly:

1. Save desired plan content to a temporary file
2. Run `erk plan save --plan-file /path/to/plan.md`
3. This bypasses the session's plan mode file

## When to Use

- Plan mode content is stale or different from intended
- Saving ad-hoc plan content without entering plan mode
- Recovering from plan content mismatch errors

## Implementation Reference

See `erk plan save --help` for flag documentation.
```

---

#### 12. Session marker lifecycle

**Location:** `docs/learned/planning/session-markers.md`
**Action:** CREATE
**Source:** [Plan]

**Draft Content:**

```markdown
---
read-when:
  - plan-save duplicate detection blocks retry
  - clearing session markers for retry scenarios
  - understanding plan-save duplicate behavior
category: planning
---

# Session Marker Lifecycle

## Overview

The `plan-saved-issue` session marker tracks which plan was saved in the current session, preventing duplicate plan creation.

## Duplicate Detection

When `plan-save` runs:
1. Checks for existing `plan-saved-issue` marker
2. If marker exists and points to valid plan, returns `skipped_duplicate: true`
3. If marker points to closed/abandoned plan, duplicate detection still blocks

## Clearing Markers for Retry

When a plan is closed/abandoned and you need to save a new plan in the same session:

```bash
erk exec marker delete --session-id <SESSION_ID> plan-saved-issue
```

Then re-run `plan-save`.

## Marker Contract

The marker serves dual purposes:
- Duplicate prevention (don't create same plan twice)
- Plan update tracking (subsequent saves update existing plan)

Deleting the marker allows creating a new plan in the same session.
```

---

#### 13. Code clarity principles update

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8163]

**Draft Content:**

```markdown
## Code Clarity: Prefer Simple Over Clever

When multiple approaches achieve the same result, prefer the more readable option:

**Prefer:** `"\n"` (string literal)
**Avoid:** `chr(10)` (character code)

**Prefer:** Direct field access (`body`)
**Avoid:** Aliases that rename fields (`body: bodyText`)

Clarity reduces cognitive load for future readers and reviewers.
```

---

### LOW Priority

#### 14. Multi-file parallel reading strategy

**Location:** `docs/learned/planning/implementation-patterns.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Multi-file Parallel Reading

When implementing from a plan, read all referenced files in parallel after understanding the plan:

1. Read `.impl/plan.md` to understand requirements
2. Identify all files mentioned in the plan
3. Read all referenced files in parallel (minimize round trips)
4. Gather complete context before writing any code

**Benefits:**
- Establishes complete context before coding
- Reduces round trips
- Enables pattern recognition across files
```

---

#### 15. PR context format reference

**Location:** `docs/learned/planning/pr-context-format.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - working with erk exec get-pr-context output
  - developing PR submission workflows
  - understanding plan context in PRs
category: planning
---

# PR Context Format Reference

## Overview

`erk exec get-pr-context` returns JSON with context for PR description generation.

## Fields

- `branch`: Current branch name
- `parent_branch`: Parent branch name
- `pr_number`: PR number (if created)
- `pr_url`: PR URL
- `diff_path`: Path to diff file
- `commit_messages`: Array of commit messages
- `plan_context`: Plan information (if associated)
  - `plan_id`: Plan issue number
  - `plan_content`: Full plan markdown
  - `objective_summary`: Linked objective summary (if any)

## Usage

The plan context enables referencing the original plan when generating PR descriptions, ensuring consistency between plan and PR body.
```

---

#### 16. Post-submission validation pattern

**Location:** `docs/learned/planning/pr-validation.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - validating PR submission completion
  - implementing PR submission workflows
  - understanding post-submission signals
category: planning
---

# Post-Submission Validation Pattern

## Overview

After PR submission, validation steps confirm completion invariants.

## Validation Commands

1. **Signal submission:** `erk exec impl-signal submitted`
   - Signals that PR has been submitted
   - Returns: `success: true, event: submitted, plan_number: <N>`

2. **Check invariants:** `erk pr check --stage=impl`
   - Validates PR completion requirements
   - Checks: .erk/impl-context/ cleanup, plan reference, draft PR status, checkout footer

## Usage

Run both commands after PR creation to confirm successful submission:

```bash
erk exec impl-signal submitted
erk pr check --stage=impl
```

Both should succeed for a complete PR submission.
```

---

## Contradiction Resolutions

No contradictions detected. All existing documentation remains valid and consistent with the new implementation patterns.

## Stale Documentation Cleanup

No stale documentation detected. All referenced files exist and phantom reference checks passed.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Missing Import After Method Addition

**What happened:** After adding `get_issues_by_numbers_with_pr_linkages()` to real.py, the method used `issue_info_to_plan` without importing it.
**Root cause:** Added method references utility from another module, forgot to check imports.
**Prevention:** Always check imports when adding methods that reference utilities from other modules; run ruff check immediately after implementation.
**Recommendation:** ADD_TO_DOC (gateway implementation checklist)

### 2. Plan Saved With Unexpected Title

**What happened:** Agent ran `plan-save` which read from session's plan mode file instead of user-provided content.
**Root cause:** Plan mode file contained stale/different content from what user intended.
**Prevention:** Before `plan-save`, verify session plan file content matches expected or use `--plan-file` override.
**Recommendation:** ADD_TO_DOC (plan-save workflow)

### 3. GraphQL Field Confusion (body vs bodyText)

**What happened:** Initially considered using `body: bodyText` alias for PullRequest.
**Root cause:** Misunderstanding of GraphQL field behavior (bodyText returns plaintext, not markdown).
**Prevention:** Review GitHub GraphQL schema before writing union type queries.
**Recommendation:** CONTEXT_ONLY (included in GraphQL pattern doc)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Gateway ABC 5-place implementation pattern

**Score:** 7/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2, Repeated pattern +1)
**Trigger:** Before adding a new gateway method
**Warning:** ALWAYS implement in all 5 places (ABC -> Real -> Fake -> DryRun -> Printing) or 3 places for PlanDataProvider (ABC -> Real -> Fake). Incomplete implementations cause runtime failures in specific modes.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because incomplete gateway implementations cause runtime failures that only manifest in specific modes (e.g., dry-run, printing). The pattern is non-obvious to developers unfamiliar with erk's gateway architecture and has high destructive potential when violated.

### 2. GraphQL issueOrPullRequest usage

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before fetching GitHub items by number
**Warning:** Use `issueOrPullRequest(number: N)` not `issue(number: N)` to handle both issues and merged PRs. Using `issue()` returns null for merged PRs.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the failure mode is silent (null returns rather than errors), affecting any GitHub item fetch where the item could be a merged PR. The pattern is non-obvious without deep GitHub GraphQL knowledge.

### 3. Roadmap-based data access preference

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, External tool quirk +1)
**Trigger:** When displaying objective-related data (plans, PRs)
**Warning:** Prefer extracting IDs from roadmap metadata and fetching targeted data rather than querying by objective_issue link. Broad queries miss closed items due to pagination limits.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because pagination limits on list queries cause silent data loss. The pattern requires understanding both GitHub GraphQL limits and erk's roadmap metadata structure.

### 4. Testing methods with complex business logic

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Destructive potential +1)
**Trigger:** Before implementing GraphQL query building or data orchestration
**Warning:** GraphQL query building, response parsing, and multi-step orchestration require unit tests covering main path and edge cases. Automated reviewers consistently flag missing tests.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because automated review tools consistently catch missing tests for complex business logic. The pattern is repeated across PRs, indicating a systemic gap in test coverage awareness.

### 5. Plan-save duplicate detection

**Score:** 4/10 (criteria: Non-obvious +2, Silent failure +2)
**Trigger:** Before saving a plan in a session that already saved one
**Warning:** Check for existing `plan-saved-issue` marker. If retrying after closing a plan, delete marker with `erk exec marker delete`.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because duplicate detection silently blocks retry attempts without clear error messaging. Agents may waste time debugging why plan-save returns `skipped_duplicate: true`.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Large file navigation with offset/limit

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** This is an agent capability pattern, not a critical failure mode. Promotion warranted if agents frequently re-read large files inefficiently.

### 2. Constructor parameter additions

**Score:** 2/10 (criteria: Cross-cutting +1, Repeated pattern +1)
**Notes:** Standard refactoring pattern with clear compiler/type checker feedback. Less urgent than silent failure patterns.
