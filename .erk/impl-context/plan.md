# Documentation Plan: Speed up erk dash Plans and Learn tabs with REST+GraphQL two-step approach

## Context

This implementation addressed significant performance bottlenecks in `erk dash` loading times for the Plans and Learn tabs. The original implementation suffered from two main issues: (1) GitHub's GraphQL `pullRequests` connection lacks an `author` filter, forcing client-side filtering that wasted bandwidth and GraphQL quota, and (2) N sequential subprocess calls to fetch learn issue states, each adding 250-400ms overhead.

The solution implemented a REST+GraphQL two-step approach: use REST API's `creator` parameter for server-side filtering, then enrich only the filtered results with a batched GraphQL query. Additionally, the expensive learn issue state fetching was removed entirely after discovering the data was only displayed in rarely-used modal views. This was a deliberate UX/performance tradeoff.

A critical lesson emerged during implementation: the "optimization" initially made performance worse. Replacing 1 subprocess call with 2 sequential subprocess calls added latency due to the ~200-300ms overhead per `gh api` invocation (Go runtime initialization + TLS handshake). This highlights that subprocess overhead often dominates API latency, and profiling should precede optimization. Future agents should understand this pattern to avoid similar pitfalls.

## Raw Materials

PR #8168

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 24    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 5     |
| Potential tripwires (score 2-3)| 4     |

## Documentation Items

### HIGH Priority

#### 1. Subprocess Overhead as Performance Bottleneck

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Part 4

**Draft Content:**

```markdown
## Subprocess Overhead in TUI Hot Paths

### Trigger
Before using `gh api` subprocess calls in TUI hot paths or performance-critical operations.

### Warning
Use `HttpClient` with httpx for direct API calls to eliminate 200-300ms process launch overhead per call. Each `gh api` subprocess spawns a Go process with overhead from: runtime initialization, auth config reads, TLS handshake to GitHub.

### Context
See `packages/erk-shared/src/erk_shared/gateway/http/` for existing HttpClient infrastructure. The codebase has `RealHttpClient` using httpx that can be injected into gateway classes.

### Example
PR #8168 initially replaced 1 GraphQL subprocess call with 2 sequential REST+GraphQL calls, which made performance worse (6.6s vs ~3s) due to doubled subprocess overhead.
```

---

#### 2. REST+GraphQL Two-Step Pattern

**Location:** `docs/learned/architecture/rest-graphql-two-step-pattern.md`
**Action:** CREATE
**Source:** [Plan] [Impl] [PR #8168]

**Draft Content:**

```markdown
---
title: REST+GraphQL Two-Step Pattern for GitHub API
read-when:
  - implementing GitHub API operations that need filtering AND rich nested data
  - hitting GraphQL filter limitations (e.g., no author filter on pullRequests)
  - optimizing GitHub API performance for TUI operations
---

# REST+GraphQL Two-Step Pattern

## Problem

GitHub's GraphQL `repository.pullRequests` connection lacks certain filters (notably `author`/`createdBy`) that the REST API supports. This forces client-side filtering that wastes bandwidth and GraphQL quota.

## Solution Pattern

1. **REST for filtering**: Use `/repos/{owner}/{repo}/issues` endpoint with query parameters (`creator`, `labels`, `state`) for server-side filtering
2. **Extract identifiers**: Get PR numbers from REST response (PRs identified by `pull_request` key presence)
3. **Apply client-side exclusions**: Filter out items with excluded labels before expensive enrichment
4. **Batched GraphQL enrichment**: Build dynamic aliased query (`pr_123: pullRequest(number: 123) { ... }`) to fetch rich fields
5. **Merge data sources**: Combine REST metadata with GraphQL enrichment into final domain objects

## Implementation

See `packages/erk-shared/src/erk_shared/gateway/github/real.py`:
- `list_plan_prs_with_details()` - orchestrates the two-step flow
- `_enrich_prs_via_graphql()` - builds and executes batched GraphQL query
- `_merge_rest_graphql_pr_data()` - merges REST and GraphQL responses

## When to Use

- GraphQL lacks a needed filter parameter (author, exclude labels)
- You need both server-side filtering AND rich nested data (reviewThreads, statusCheckRollup)
- Reducing GraphQL quota consumption is important

## When NOT to Use

- When subprocess overhead dominates (see tripwires). A single batched GraphQL query can beat multi-step approaches.
- When the user is the only/primary author (minimal reduction from filtering)

## Performance Characteristics

- Reduces data transfer proportional to filter selectivity
- Saves GraphQL quota (only enriches filtered results)
- BUT: adds round-trip latency
- Critical: only beneficial when using HttpClient (not subprocess-based gh CLI)

## Related

- `docs/learned/architecture/github-cli-limits.md` - REST API alternatives
- `docs/learned/architecture/gateway-abc-implementation.md` - 5-place implementation pattern
```

---

#### 3. Learn Issue State Removal

**Location:** `docs/learned/planning/learn-issue-state-removal.md`
**Action:** CREATE
**Source:** [Plan] [Impl] Part 2 [PR #8168]

**Draft Content:**

```markdown
---
title: Learn Issue State Removal (Performance Tradeoff)
read-when:
  - considering adding back learn issue state fetching
  - designing similar UX/performance tradeoffs
  - understanding why learn modal shows clipboard icon instead of checkmark
---

# Learn Issue State Removal

## Decision

The `_fetch_learn_issue_states()` method was removed from `RealPlanDataProvider` to eliminate N sequential API calls.

## Performance Cost (Before)

- N sequential `gh api` subprocess calls (one per learn plan)
- Each call: 250-400ms (subprocess overhead + API latency)
- 10 learn plans: 2.5-4 seconds
- 30 learn plans: 7.5-12 seconds

## UX Impact

- Learn modal no longer shows open/closed state icon
- Always displays clipboard icon instead of checkmark for closed issues
- Learn issue number still displayed and clickable (users can check GitHub directly)

## Rationale

The marginal UX value of distinguishing open vs closed learn issues did not justify the multi-second load time cost imposed on every dashboard load. The information is still accessible via one click.

## When to Reconsider

If learn issue state becomes critical to workflows (e.g., automated cleanup, status reporting), consider:
1. Batched GraphQL query with aliased issue lookups
2. Background async fetching with progressive UI update
3. Server-side state caching

## Implementation

The method was deleted from `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`. The `_build_row_data()` method now passes `learn_plan_issue_closed=None` unconditionally.
```

---

#### 4. ABC Exemption Rules for Default Parameters

**Location:** `docs/learned/architecture/abc-exemption-rules.md`
**Action:** CREATE
**Source:** [PR #8168 comments]

**Draft Content:**

```markdown
---
title: ABC Exemption Rules for Default Parameters
read-when:
  - seeing automated review flags about default parameters in ABC methods
  - wondering when default parameter prohibition doesn't apply
  - resolving false positives from dignified-python review
---

# ABC Exemption Rules for Default Parameters

## Context

The dignified-python standard prohibits default parameter values (`def foo(verbose=False)` is forbidden). However, certain contexts are exempt from this rule.

## Exemptions

### 1. ABC Abstract Methods

Abstract method signatures in ABCs may use default values to establish the contract. This is intentional: the ABC defines what defaults implementations must honor.

```python
class GitHubGateway(ABC):
    @abstractmethod
    def list_plan_prs_with_details(
        self,
        *,
        exclude_labels: list[str] = (),  # Allowed in ABC
    ) -> list[PlannedPR]:
        pass
```

### 2. ABC Implementations MUST Match Contract

When implementing an ABC, the implementation signature must match the ABC's signature exactly, including any default values.

### 3. Fake Classes for Testing

Fake implementations may use defaults for test convenience, especially for parameters that don't affect the fake's behavior.

## Resolution for Automated Reviews

When automated reviewers flag ABC default parameters:
1. Check if the flagged method is an ABC abstract method
2. Check if the class is a Fake implementation
3. If either is true, the flag is a false positive

## Related

- `docs/learned/architecture/gateway-abc-implementation.md` - 5-place pattern
- `.claude/reviews/dignified-python.md` - base review rules
```

---

#### 5. Automated Review Conflict Resolution

**Location:** `docs/learned/ci/automated-review-conflicts.md`
**Action:** CREATE
**Source:** [PR #8168 comments]

**Draft Content:**

```markdown
---
title: Automated Review Conflict Resolution
read-when:
  - multiple automated reviewers flag the same code differently
  - understanding precedence between reviewers
  - resolving conflicting review feedback
---

# Automated Review Conflict Resolution

## Problem

Multiple automated reviewers may flag the same code with different assessments. For example:
- Dignified Code Simplifier flags a default parameter
- Dignified Python Review confirms it's an ABC exemption

## Precedence Hierarchy

1. **Semantic analysis** takes precedence over **pattern matching**
   - If a reviewer with deeper context (e.g., ABC awareness) approves, that supersedes surface-level pattern flags

2. **Specific exemptions** override **general rules**
   - ABC exemption rules override the general "no default parameters" rule

3. **Explicit confirmations** resolve ambiguity
   - When a reviewer explicitly states "exemption applies", treat as resolved

## How to Recognize Exemptions

Look for phrases in review comments like:
- "ABC abstract method - defaults allowed"
- "Fake implementation - exemption applies"
- "Pattern is intentional for [reason]"

## Escalation

If reviewers produce genuinely conflicting assessments (not exemption vs rule), escalate to human review by adding a comment requesting clarification.

## Related

- `docs/learned/architecture/abc-exemption-rules.md` - specific ABC exemptions
- `.claude/reviews/` - review configurations
```

---

### MEDIUM Priority

#### 6. Git Batch Operations Pattern

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Parts 4-5

**Draft Content:**

```markdown
## Git Batch Operations

### Trigger
Before implementing sequential git operations for batch data (e.g., fetching commit SHAs for multiple branches).

### Warning
Use `git for-each-ref` or similar batch commands instead of N individual `git rev-parse` calls. Each subprocess adds ~5-10ms overhead; with 50 branches, this adds 250-500ms.

### Correct Pattern
```bash
# Batch: single subprocess (~5ms)
git for-each-ref refs/heads/ --format='%(refname:short) %(objectname)'

# Instead of N subprocesses (N * ~5-10ms)
for branch in branches:
    git rev-parse $branch
```

### Example
`get_all_branches()` in `packages/erk-shared/src/erk_shared/gateway/graphite/real.py` was identified as calling `git rev-parse` per branch. The fix uses `git for-each-ref`.

See `get_all_branch_sync_info()` for existing batch pattern at line ~275 of the same file.
```

---

#### 7. Pre-Enrichment Filtering Pattern

**Location:** `docs/learned/architecture/exclude-labels-pattern.md`
**Action:** CREATE
**Source:** [Impl] Part 3 [PR #8168]

**Draft Content:**

```markdown
---
title: Pre-Enrichment Filtering Pattern (exclude_labels)
read-when:
  - adding filtering to operations with expensive enrichment steps
  - implementing label exclusion for GitHub API operations
  - optimizing batched API operations
---

# Pre-Enrichment Filtering Pattern

## Problem

Batched GraphQL enrichment is expensive (API quota, latency). Enriching items that will be filtered out client-side wastes resources.

## Solution

Apply exclusion filters BEFORE expensive enrichment operations:

1. Fetch lightweight data (REST API)
2. Apply `exclude_labels` filter on cheap response
3. Only then run expensive GraphQL enrichment on remaining items

## Implementation Example

The `list_plan_prs_with_details()` method:
1. Fetches issues via REST (labels in response)
2. Filters out items with excluded labels
3. Enriches only remaining items via GraphQL

## Parameter Propagation

The `exclude_labels` parameter flows through 5 gateway implementations:
- ABC: `packages/erk-shared/src/erk_shared/gateway/github/abc.py`
- Real: `packages/erk-shared/src/erk_shared/gateway/github/real.py`
- Fake: `packages/erk-shared/src/erk_shared/gateway/github/fake.py`
- DryRun: `packages/erk-shared/src/erk_shared/gateway/github/dry_run.py`
- Printing: `packages/erk-shared/src/erk_shared/gateway/github/printing.py`

## Why Not Server-Side Exclusion?

GitHub REST API `labels` parameter only supports AND (inclusion). There's no "NOT label" syntax. Client-side exclusion before enrichment is the best available approach.
```

---

#### 8. Plans/Learn Tab Server-Side Filtering

**Location:** `docs/learned/tui/plans-learn-tab-filtering.md`
**Action:** CREATE
**Source:** [Impl] Part 2 [PR #8168]

**Draft Content:**

```markdown
---
title: Plans/Learn Tab Server-Side Filtering
read-when:
  - understanding how Plans and Learn tabs fetch different data
  - modifying tab filtering behavior
  - optimizing TUI data loading
---

# Plans/Learn Tab Server-Side Filtering

## Architecture

Plans and Learn tabs now split server-side via label configuration:

| Tab    | Labels Query                   | Exclude Labels     |
|--------|-------------------------------|--------------------|
| Plans  | `("erk-plan",)`               | `("erk-learn",)`   |
| Learn  | `("erk-plan", "erk-learn")`   | `()`               |

## Implementation

View configurations in `src/erk/tui/views/types.py`:
- `PLANS_VIEW`: Standard plans with learn plans excluded
- `LEARN_VIEW`: Only learn-related plans (requires both labels)

## Performance Impact

Previously both tabs fetched ALL `erk-plan` labeled items and filtered client-side. Now:
- Plans tab: Server-side filtering via REST, then exclude `erk-learn` before enrichment
- Learn tab: Server-side AND query for both labels

This reduces data transfer and GraphQL quota usage.

## Cache Behavior

Different label combinations create different cache keys, ensuring tabs maintain separate cached datasets.
```

---

#### 9. HttpClient Injection for Performance

**Location:** `docs/learned/architecture/http-client-usage.md`
**Action:** CREATE
**Source:** [Impl] Part 4

**Draft Content:**

```markdown
---
title: HttpClient Usage for Performance-Critical Operations
read-when:
  - implementing TUI features with frequent API calls
  - bypassing subprocess overhead for GitHub operations
  - understanding when to use HttpClient vs gh CLI
---

# HttpClient Usage for Performance-Critical Operations

## Context

The codebase has an `HttpClient` ABC with `RealHttpClient` implementation using httpx. This enables direct HTTP requests without subprocess overhead.

## When to Use HttpClient

- TUI data loading operations
- Operations called in loops or batches
- Performance-critical paths where 200-300ms matters

## When to Use gh CLI Subprocess

- One-off CLI commands
- Operations requiring gh CLI-specific features
- Less frequent operations where convenience trumps speed

## Implementation

The HttpClient lives at `packages/erk-shared/src/erk_shared/gateway/http/`:
- `abc.py`: HttpClient ABC with `get()`, `post()`, `patch()` methods
- `real.py`: RealHttpClient using httpx

## Injection Pattern

Currently used in `RealPlanDataProvider` for operations like `close_plan` and `fetch_plan_content`. Token is fetched once at startup via `fetch_github_token()` and reused.

## Limitation

Current `get()` returns `dict[str, Any]`. For list endpoints (like REST issues), the service layer needs to handle the response type appropriately.
```

---

#### 10. Test Coverage for Private Gateway Helpers

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [PR #8168]

**Draft Content:**

```markdown
## Private Gateway Helper Testing

When adding private helper methods to gateway implementations (e.g., `_enrich_prs_via_graphql`, `_merge_rest_graphql_pr_data`), write comprehensive edge case tests:

### Test Categories

1. **Single item**: Verify basic functionality
2. **Multiple items**: Verify batching works correctly
3. **Empty input**: Graceful handling of empty lists
4. **Partial data**: Some items have data, others don't
5. **API failures**: Graceful degradation when enrichment fails

### Example from PR #8168

`tests/integration/test_real_github_pr_enrichment.py` contains 12 tests covering:
- Single PR enrichment
- Multiple PR enrichment
- Empty PR list handling
- Missing GraphQL data (returns REST-only data)
- Malformed responses

### Test Fixture Patterns

- `_make_graphql_pr_node()`: Creates mock GraphQL PR node
- `_make_rest_pr_item()`: Creates mock REST issue item
- Mock subprocess patterns for testing enrichment without real API calls
```

---

#### 11. Gateway ABC Implementation - Add Discovery Pattern

**Location:** `docs/learned/architecture/gateway-abc-implementation.md`
**Action:** UPDATE
**Source:** [Impl] Part 1

**Draft Content:**

```markdown
## Discovery Pattern Before Modification

Before modifying any gateway method signature:

1. **Grep for all implementations**:
   ```bash
   grep -r "def method_name" packages/erk-shared/src/erk_shared/gateway/
   ```

2. **Check all 5 places**:
   - ABC (abstract signature)
   - Real (production implementation)
   - Fake (test double)
   - DryRun (logging wrapper)
   - Printing (output wrapper)

3. **Check callers**:
   ```bash
   grep -r "\.method_name(" src/ packages/
   ```

4. **Update in order**:
   1. ABC first (establishes contract)
   2. Real implementation
   3. Fake implementation
   4. DryRun/Printing (usually delegation only)
   5. All callers

This grep-before-modify pattern prevents missing implementations during gateway updates.
```

---

#### 12. Performance Optimization - Adding Round-Trips Warning

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Part 4

**Draft Content:**

```markdown
## Adding Round-Trips as Optimization

### Trigger
Before "optimizing" by splitting one API call into multiple sequential calls.

### Warning
Single batched GraphQL queries often outperform multi-step REST+GraphQL approaches due to subprocess overhead. Profile before optimizing. The overhead of 2 subprocess calls (~400-600ms) may exceed savings from reduced data transfer.

### Example
PR #8168 initially replaced 1 GraphQL subprocess call with 2 sequential REST+GraphQL calls. Despite "smart" server-side filtering, performance degraded from ~3s to 6.6s because subprocess overhead dominated.

### Recommendation
1. Profile actual bottlenecks before optimizing
2. Calculate subprocess overhead separately from network latency
3. Consider httpx for performance-critical paths to eliminate subprocess overhead
4. Test with realistic data volumes
```

---

#### 13. Automated Review Iteration Lifecycle

**Location:** `docs/learned/ci/review-iteration-lifecycle.md`
**Action:** CREATE
**Source:** [PR #8168 comments]

**Draft Content:**

```markdown
---
title: Automated Review Iteration Lifecycle
read-when:
  - understanding why automated reviews run multiple times
  - tracking review violation resolution
  - debugging review behavior
---

# Automated Review Iteration Lifecycle

## Expected Behavior

Automated reviews run on every push to a PR branch. This is normal and expected:

1. Initial review identifies violations
2. Developer addresses violations
3. Review re-runs on new commit
4. Process repeats until all violations resolved

## PR #8168 Example

The PR went through 6 review iterations tracking:
- Initial default parameter flags
- ABC exemption confirmations
- Line length fixes
- Format corrections

Each iteration tracked timestamps and resolution status.

## Timestamps

Review comments include timestamps for tracking when violations were identified and resolved. This enables auditing of the review process.

## Violation Tracking

Violations are tracked through to resolution. A violation is considered resolved when:
- Code is changed to address the issue
- Exemption is explicitly confirmed
- Manual override is applied (with justification)
```

---

#### 14. Graphite Tracking Error Recovery

**Location:** `docs/learned/planning/plan-save-troubleshooting.md`
**Action:** CREATE
**Source:** [Impl] Part 6

**Draft Content:**

```markdown
---
title: Graphite Tracking Error Recovery
read-when:
  - seeing "not in the history of" errors from gt track
  - plan-save fails mid-operation
  - cleaning up stale branches after failed operations
---

# Graphite Tracking Error Recovery

## Problem

When plan-save fails mid-operation, it may leave behind a stale branch with broken parent tracking. Retrying fails with:
```
plnd/{old-slug} is not in the history of plnd/{new-slug}
```

## Diagnostic Steps

1. **List branches matching the slug pattern**:
   ```bash
   git branch --list "plnd/{slug}*"
   ```

2. **Verify the branch is stale** (not pushed, no important commits)

3. **Check parent relationship**:
   ```bash
   git merge-base --is-ancestor {expected-parent} {stale-branch}
   ```

## Recovery Procedure

1. **Delete the stale branch**:
   ```bash
   git branch -D plnd/{stale-branch-name}
   ```

2. **Verify parent relationship is intact** for current HEAD

3. **Retry the plan-save operation**

## Prevention

Before creating a plan branch, the plan-save workflow should check if a branch with the matching slug already exists and prompt for cleanup.
```

---

### LOW Priority

#### 15. Filter-Before-Enrich Performance Pattern

**Location:** `docs/learned/architecture/performance-patterns.md`
**Action:** CREATE
**Source:** [Impl] Part 2

**Draft Content:**

```markdown
---
title: Filter-Before-Enrich Performance Pattern
read-when:
  - designing data fetching pipelines
  - optimizing API-heavy operations
---

# Filter-Before-Enrich Performance Pattern

## Principle

Apply filters as early as possible in the data pipeline to minimize expensive operations on data that will be discarded.

## Pipeline Order

1. **Server-side filtering** (API query parameters)
2. **Client-side label exclusion** (cheap, on lightweight data)
3. **Lazy GraphQL enrichment** (expensive, only on remaining items)

## Example

Plans tab loading:
1. REST issues list with `labels=erk-plan` (server-side)
2. Exclude items with `erk-learn` label (client-side, before enrichment)
3. Batched GraphQL enrichment (only for remaining items)
```

---

#### 16. Tripwires Review Two-Tier Verification

**Location:** `docs/learned/ci/tripwires-review-tiers.md`
**Action:** CREATE
**Source:** [PR #8168 comments]

**Draft Content:**

```markdown
---
title: Tripwires Review Two-Tier Verification
read-when:
  - understanding how tripwires review works
  - debugging tripwire detection
---

# Tripwires Review Two-Tier Verification

## Strategy

The tripwires review uses a two-tier verification approach:

### Tier 1: Mechanical Pattern Matching

Direct regex/AST pattern detection:
- `subprocess.run` without wrapper
- `gt` commands without `--no-interactive`
- `os.path` usage (should be pathlib)

### Tier 2: Semantic LLM-Derived Matches

Context-aware detection requiring understanding:
- 5-place gateway implementation violations
- ABC signature mismatches
- Missing test coverage for edge cases

## False Positive Handling

Tier 1 matches are high-confidence but may miss context (e.g., test code).
Tier 2 matches provide context but may have lower confidence.

Combined, they provide comprehensive coverage with reasonable precision.
```

---

#### 17. Implementation Session Exploration Phase

**Location:** `docs/learned/planning/plan-implement-workflow.md`
**Action:** UPDATE
**Source:** [Impl] Part 1

**Draft Content:**

```markdown
## Exploration Phase (for Complex Plans)

For plans affecting core abstractions (gateways, frozen dataclasses, pipeline steps), add an exploration phase between reading the plan and creating todos:

1. **Grep for all affected classes/methods**
2. **Read all implementations** (ABC + real + fake + dry_run + printing)
3. **Trace data flow** through service -> provider -> gateway layers
4. **Identify all frozen dataclass update sites**
5. **Build mental model** BEFORE creating todo entries

This front-loaded exploration prevents mid-implementation discovery of missing update sites.

### Example

PR #8168 implementation session spent significant time in exploration:
- Traced `list_plan_prs_with_details` across 5 gateway files
- Identified persisted output file handling pattern
- Found client-side filtering location (app.py)
- Mapped relationship between PlanListService and GitHub gateway
```

---

#### 18. Persisted Output File Handling

**Location:** `docs/learned/claude-code/capabilities.md`
**Action:** UPDATE
**Source:** [Impl] Part 1

**Draft Content:**

```markdown
## Persisted Output Files

When tool outputs exceed inline display limits (~20KB), Claude Code saves them to `.claude/projects/.../tool-results/` and shows a `<persisted-output>` indicator.

### Handling

1. The tool will display a path like: `tool-results/toolu_xxx.txt`
2. Use the Read tool to access the full content: `Read(file_path="~/.claude/projects/.../tool-results/toolu_xxx.txt")`
3. This is common for:
   - Large grep results
   - Multi-file diffs
   - Verbose command output

### Pattern

When you see persisted output, always read the file to access complete results. The inline display is truncated.
```

---

#### 19. Branch Slug Generation Algorithm

**Location:** `docs/learned/planning/plan-save-workflow.md`
**Action:** UPDATE
**Source:** [Impl] Part 6

**Draft Content:**

```markdown
## Branch Slug Generation

When generating branch slugs for plan-save:

### Rules

1. **2-4 words**: Keep it concise but descriptive
2. **Action verb first**: Start with what the plan does (add, fix, update, batch)
3. **Distinctive essence**: Include key nouns that differentiate this plan
4. **Max 30 characters**: Slug portion (before date suffix)

### Examples

| Plan Title | Good Slug | Why |
|------------|-----------|-----|
| "Fix: Replace N git rev-parse calls with single git for-each-ref" | `batch-graphite-branch-heads` | Action (batch) + distinctive nouns |
| "Speed up erk dash Plans and Learn tabs" | `speedup-dash-loading` | Action + target |
| "Add exclude_labels parameter to gateway" | `add-exclude-labels` | Action + feature |

### Anti-patterns

- Too long: `fix-replace-n-git-rev-parse-calls-with-single-git-for-each-ref`
- Too vague: `performance-fix`
- No action verb: `graphite-branch-changes`
```

---

#### 20. Plan Scope Pivoting Workflow

**Location:** `docs/learned/planning/planning-workflow.md`
**Action:** UPDATE
**Source:** [Impl] Part 5

**Draft Content:**

```markdown
## Plan Scope Pivoting

When developing comprehensive plans, be prepared for user feedback to narrow scope:

### Pattern

1. **Create comprehensive plan**: Document all identified optimizations/changes
2. **Present to user**: Show the full analysis with tradeoffs
3. **Receive feedback**: User may want to focus on subset
4. **Pivot cleanly**: Extract the focused subset into a new plan

### Example from PR #8168

Initial plan included:
- GitHub API httpx migration
- git for-each-ref optimization
- Parallel operation execution

User requested focus on just the git optimization. Agent successfully extracted that subset into a standalone plan.

### Key Behaviors

- Don't treat comprehensive analysis as wasted work
- The analysis informs future plans
- Clean extraction requires well-structured initial plans
- Acknowledge user scope preferences quickly
```

---

#### 21. Update GitHub Interface Patterns

**Location:** `docs/learned/architecture/github-interface-patterns.md`
**Action:** UPDATE
**Source:** [Plan] Part 1

**Draft Content:**

```markdown
## REST vs GraphQL Filter Comparison

| Filter        | REST Issues | GraphQL pullRequests | GraphQL search |
|---------------|-------------|---------------------|----------------|
| author/creator| `creator=X` | NOT AVAILABLE       | `author:X`     |
| labels (AND)  | `labels=A,B`| `labels: [A, B]`    | `label:A label:B` |
| labels (NOT)  | NOT AVAILABLE| NOT AVAILABLE      | `-label:X`     |
| state         | `state=open`| `states: [OPEN]`    | `is:open`      |
| repo          | In URL      | In URL              | `repo:owner/repo` |

### Key Insight

When you need author filtering for PRs, you cannot use `repository.pullRequests` directly. Options:
1. GraphQL `search(type: ISSUE)` with `author:` qualifier
2. REST `/repos/{owner}/{repo}/issues?creator=X` (PRs included, identified by `pull_request` key)
3. Hybrid: REST filtering + GraphQL enrichment
```

---

#### 22. Update Planned PR Backend

**Location:** `docs/learned/planning/planned-pr-backend.md`
**Action:** UPDATE
**Source:** [PR #8168]

**Draft Content:**

```markdown
## Migration from GET_PLAN_PRS_WITH_DETAILS_QUERY

PR #8168 migrated from a monolithic GraphQL query to REST+GraphQL two-step approach:

### Before
- Single `GET_PLAN_PRS_WITH_DETAILS_QUERY` GraphQL query
- Client-side author filtering
- Downloaded all PRs, filtered after

### After
- REST issues endpoint with `creator` parameter
- Client-side `exclude_labels` filtering before enrichment
- Batched GraphQL enrichment for rich fields only

### Cross-Reference
See `docs/learned/architecture/rest-graphql-two-step-pattern.md` for the complete pattern documentation.
```

---

#### 23. Update TUI Data Contract

**Location:** `docs/learned/tui/data-contract.md`
**Action:** UPDATE
**Source:** [PR #8168]

**Draft Content:**

```markdown
## Performance Optimization Patterns

### Batched API Calls
Instead of N sequential API calls, use batched approaches:
- GraphQL aliased queries for multiple entities
- REST pagination with filtering

### REST List + GraphQL Enrich
For operations needing both filtering and rich data:
1. REST API for server-side filtering (smaller response)
2. GraphQL for enrichment (rich nested fields)

### Lazy Loading
Only fetch data when needed:
- Detail-only data fetched on modal open
- Expensive state lookups deferred or eliminated

## Filter Fields

### PlanFilters.exclude_labels

Tuple of label strings to exclude from results. Applied client-side after REST fetch but before GraphQL enrichment to minimize API budget waste.

### ViewConfig.exclude_labels

View-level configuration for label exclusion. Different views can specify different exclusion rules (e.g., Plans view excludes "erk-learn").
```

---

#### 24. GitHub Enrichment Testing Patterns

**Location:** `docs/learned/testing/github-enrichment-testing.md`
**Action:** CREATE
**Source:** [PR #8168]

**Draft Content:**

```markdown
---
title: GitHub Enrichment Testing Patterns
read-when:
  - writing tests for GitHub gateway methods
  - testing REST+GraphQL hybrid operations
  - creating mock fixtures for GitHub API responses
---

# GitHub Enrichment Testing Patterns

## Test Fixtures

See `tests/integration/test_real_github_pr_enrichment.py` for reusable patterns.

### GraphQL PR Node

```python
def _make_graphql_pr_node(number: int, ...) -> dict:
    """Create mock GraphQL pullRequest node."""
    # Include: number, title, headRefName, commits, reviewThreads, etc.
```

### REST Issue Item

```python
def _make_rest_pr_item(number: int, ...) -> dict:
    """Create mock REST issue item (with pull_request key)."""
    # Include: number, title, labels, user, html_url, etc.
```

### Mock Subprocess

Use `mocker.patch` to mock `execute_gh_command_with_retry` for both REST and GraphQL calls. Return appropriate mock data for each call.

## Edge Case Coverage

1. **Empty list**: Verify no API calls made
2. **Single item**: Basic enrichment works
3. **Multiple items**: Batching constructs correct query
4. **Missing enrichment data**: Graceful fallback to REST-only data
5. **API failure**: Appropriate error handling

## Testing Merge Logic

The merge function (`_merge_rest_graphql_pr_data`) should be tested separately:
- REST-only data preserved when GraphQL enrichment fails
- GraphQL data properly merged into REST base
- All fields correctly mapped
```

---

## Contradiction Resolutions

No contradictions found. Existing documentation is consistent with new insights:
- REST API preference for programmatic access (rate limit separation)
- GraphQL for data not available in REST (PR review threads, complex nested queries)
- Enrich-before-filter pipeline ordering
- Batched queries to avoid N+1 problems

---

## Stale Documentation Cleanup

No stale documentation detected. All referenced files and methods verified:
- `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py` EXISTS
- `packages/erk-shared/src/erk_shared/gateway/github/real.py` EXISTS
- `list_plan_prs_with_details()` method EXISTS
- `_enrich_prs_via_graphql()`, `_merge_rest_graphql_pr_data()` EXISTS
- `PlanRowData`, `RealPlanDataProvider` EXISTS

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Performance "Optimization" Made Things Slower

**What happened:** Replaced 1 GraphQL subprocess call with 2 sequential REST+GraphQL calls. Performance degraded from ~3s to 6.6s.

**Root cause:** Each `gh api` subprocess adds 200-300ms overhead (Go runtime initialization + TLS handshake). Two calls = 400-600ms overhead before any actual API work. Subprocess overhead dominated API latency.

**Prevention:** Profile actual bottlenecks before optimizing. Calculate subprocess overhead separately from network latency. Consider httpx for performance-critical paths.

**Recommendation:** TRIPWIRE

### 2. N+1 Subprocess Calls in Batch Operations

**What happened:** `get_all_branches()` called `git rev-parse` for each tracked branch individually. With 30-50 branches, this added 150-500ms overhead.

**Root cause:** Loop-based single-item operations instead of batch command.

**Prevention:** Check for batch variants of commands before implementing loops. Use `git for-each-ref` instead of N `git rev-parse` calls.

**Recommendation:** TRIPWIRE

### 3. Overfetching with Client-Side Filtering

**What happened:** GraphQL `pullRequests` connection lacks `author` filter. Code fetched all PRs and filtered client-side, wasting bandwidth and quota.

**Root cause:** API lacks needed filter parameter.

**Prevention:** Always check API docs for filter params before implementing client-side filtering. Consider REST→GraphQL two-step if GraphQL lacks filter.

**Recommendation:** ADD_TO_DOC (tripwires already cover this)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Subprocess Overhead in gh CLI

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before using `gh api` subprocess calls in TUI hot paths

**Warning:** Use `HttpClient` with httpx for direct API calls to eliminate 200-300ms process launch overhead per call

**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because it's non-obvious (developers expect API latency to dominate, not process spawn), affects all TUI operations using gh CLI, and fails silently (code works, just slowly). PR #8168 demonstrated the harm: a well-intentioned optimization made things 2x slower.

### 2. Git Batch Operations

**Score:** 4/10 (Cross-cutting +2, Repeated pattern +1, External tool quirk +1)

**Trigger:** Before implementing sequential git operations for batch data

**Warning:** Use `git for-each-ref` or similar batch commands instead of N individual `git rev-parse` calls

**Target doc:** `docs/learned/architecture/tripwires.md`

The pattern is cross-cutting (applies to any git batch operation), and the codebase already has examples of both the anti-pattern and the correct approach.

### 3. Adding Round-Trips as Optimization

**Score:** 4/10 (Non-obvious +2, Silent failure +2)

**Trigger:** Before "optimizing" by splitting one API call into multiple

**Warning:** Single batched GraphQL queries often faster than multi-step REST+GraphQL approaches due to subprocess overhead. Profile before optimizing.

**Target doc:** `docs/learned/architecture/tripwires.md`

Non-obvious because "smart" filtering sounds like it should help. Silent failure because code works correctly, just slower.

### 4. Client-Side Filtering After API Fetch

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)

**Trigger:** When implementing filtering logic after API data fetch

**Warning:** Check if filter can be pushed server-side to reduce payload. Look for `if field == value: continue` patterns in parsing code.

**Target doc:** `docs/learned/architecture/tripwires.md`

Cross-cutting pattern that affects any API operation where filtering happens post-fetch.

### 5. Pre-Enrichment Filtering

**Score:** 4/10 (Cross-cutting +2, Non-obvious +2)

**Trigger:** When adding expensive batched API enrichment operations

**Warning:** Apply exclusion filters BEFORE enrichment to avoid wasting API budget on items you'll discard

**Target doc:** `docs/learned/architecture/tripwires.md`

The filter-before-enrich principle is non-obvious and applies broadly to any pipeline with expensive enrichment steps.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Missing --no-interactive on gt Commands

**Score:** 3/10 (Cross-cutting +2, External tool quirk +1)

**Notes:** Already documented as a universal tripwire. No promotion needed.

### 2. N+1 Subprocess Calls in Batch Operations

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)

**Notes:** Covered by the git batch operations tripwire above. Could be generalized to all subprocess batch operations, not just git.

### 3. Assuming Server-Side Filtering Always Wins

**Score:** 2/10 (Non-obvious +2)

**Notes:** Didn't meet threshold because the benefit depends heavily on selectivity. When the user is the only/primary author, server-side filtering provides minimal reduction while adding round-trip cost.

### 4. Graphite Tracking Error Recovery

**Score:** 2/10 (External tool quirk +2)

**Notes:** Specific to plan-save workflow. Documented in troubleshooting guide rather than as tripwire.

---

## Cornerstone Redirects (SHOULD_BE_CODE)

### 1. Conditional API Routing Pattern

**Why:** Decision logic for when to use REST vs GraphQL belongs in code comments, not docs.

**Action:** Add comment in `list_plan_prs_with_details()` explaining the routing logic and why two-step was chosen.

### 2. ViewConfig Filtering Fields

**Why:** Dataclass field documentation belongs in docstrings, not learned docs.

**Action:** Enhance `ViewConfig` and `PlanFilters` docstrings with field explanations for `exclude_labels` and its role in the filtering pipeline.

---

## Attribution

Documentation opportunities identified by:

- **SessionAnalyzer** (8 sessions): Pattern discovery, external lookups, error resolution, prevention insights
- **CodeDiffAnalyzer**: Inventory of 47 code changes, 12 documentation recommendations
- **ExistingDocsChecker**: Verified 10 high-relevance docs, found 0 contradictions, 0 stale references
- **PRCommentAnalyzer**: 7 documentation opportunities from automated review conflicts and resolutions

Total context analyzed: ~220k tokens across sessions, diffs, docs, and PR comments
