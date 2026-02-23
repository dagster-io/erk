# Documentation Plan: Add stacked PR emoji to dashboard

## Context

PR #7964 added the pancake emoji (stacked PR indicator) to the erk dashboard. The implementation threads a new `is_stacked` boolean through the lifecycle indicator pipeline, computed from a dual-source detection strategy: GitHub's `base_ref_name` field (primary) plus a Graphite `get_parent_branch()` fallback for plan PRs that always target master on GitHub even when Graphite-stacked. A new `base_ref_name` field was added to `PullRequestInfo`, requiring updates across three separate parsers (GraphQL timeline, GraphQL details, REST batch). The PR also introduced the concept of "informational" vs. "blocking" indicators, where the pancake emoji does not prevent the rocket emoji from appearing in the implemented stage.

Beyond the stacked indicator itself, the PR included several ancillary changes: deletion of `get_plan_backend()` and `PlanBackendType` (PR #7971), removal of `push-and-create-pr` and `set-local-review-marker` exec commands, removal of the `github_admin` context parameter, and a two-tier polling backoff strategy for GitHub workflow runs. Several existing docs now have phantom references to deleted code.

Documentation matters here because the three-parser update pattern for `PullRequestInfo` is a silent-failure trap that no agent would discover without explicit guidance. The blocking vs. informational indicator classification is a design rule that future indicator authors must follow or risk breaking the rocket emoji display. And several existing docs reference deleted functions and stale line numbers that will mislead agents.

## Raw Materials

Session 464d1dc0-a118-4390-adc6-8b75c1eb5a18 (learn session used as fallback proxy for implementation session bb4a46c2)

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 8     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 3     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action. These must be resolved before or alongside new content creation.

### 1. Update `draft-pr-plan-backend.md` to remove phantom references

**Location:** `docs/learned/planning/draft-pr-plan-backend.md`
**Action:** UPDATE
**Source:** [PR #7971]

**Cleanup Instructions:**

The "Backend Selection" section describes `get_plan_backend()` and `PlanBackendType`, both deleted in commit `4ccfbb0c0` (PR #7971). The "Land Pipeline Integration" section references `close_review_pr()` at `land_pipeline.py:469-471`, which is a phantom -- this function does not exist anywhere in `src/`.

```markdown
## Backend Selection

<!-- REWRITE: The previous content described `get_plan_backend()` and `PlanBackendType`,
     which were deleted in PR #7971. Describe the current backend resolution mechanism.
     See `packages/erk-shared/src/erk_shared/plan_store/__init__.py` for the current
     implementation. The default backend is now `draft_pr`. -->
```

Additionally, remove the `close_review_pr()` reference entirely from the Land Pipeline Integration section -- the function does not exist.

### 2. Fix phantom line numbers in `visual-status-indicators.md`

**Location:** `docs/learned/desktop-dash/visual-status-indicators.md`
**Action:** UPDATE_REFERENCES
**Source:** [Impl]

**Cleanup Instructions:**

Two line number citations are stale:
- `lifecycle.py:61-140` should point to where `format_lifecycle_with_status()` actually starts (approximately line 111). Grep for `def format_lifecycle_with_status` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py` to find the correct line.
- `real.py:639,727-731` claims to show where `review_decision` is wired, but line 639 is URL-parsing code (`run_url`), not `review_decision`. Grep for `review_decision` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` to find the correct lines.

Per `docs/learned/documentation/source-pointers.md`, prefer file-level pointers over line numbers to reduce future staleness.

## Documentation Items

### HIGH Priority

#### 1. Create stacked PR indicator documentation

**Location:** `docs/learned/tui/stacked-pr-indicator.md`
**Action:** CREATE
**Source:** [PR #7964]

**Draft Content:**

```markdown
---
read-when: adding dashboard indicators, working with stacked PRs, modifying lifecycle display
category: tui
tripwires: 1
---

# Stacked PR Indicator

The pancake emoji indicates a PR that targets a non-trunk branch (i.e., is part of a Graphite stack).

## When It Appears

A PR is considered stacked when `base_ref_name` is not `master` or `main`. This is computed in
`_build_row_data()`. See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`
(grep for `pr_is_stacked`).

## Dual-Source Detection

Two sources are needed because plan PRs always target master on GitHub, even when Graphite-stacked:

1. **GitHub `base_ref_name`** (primary): Populated on `PullRequestInfo` from the GitHub API.
   If `base_ref_name` is not master/main, the PR is stacked.
2. **Graphite local stack tracking** (fallback): Uses `branch_manager.get_parent_branch()` to
   check whether the head branch's local Graphite parent is a non-trunk branch. Needed for
   plan PRs where GitHub always shows master as the base.

See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` (grep for
`get_parent_branch`).

## Indicator Ordering

The stacked emoji is inserted as the **first** indicator in `_build_indicators()`, before
draft/conflict/publish indicators. This ensures stack status is always visible regardless
of other lifecycle state.

## Blocking vs. Informational Classification

The stacked indicator is **informational** -- it does NOT block the rocket emoji from appearing
in the implemented stage. The mechanism uses `has_blocking_indicators` to check whether any
non-informational indicators exist. See the "Blocking vs. Informational Indicators" section
in `docs/learned/desktop-dash/visual-status-indicators.md`.

Future indicator authors: if your indicator should be informational (non-blocking), it must
be excluded from the `has_blocking_indicators` check. See
`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`
(grep for `has_blocking_indicators`).

## Data Flow

`base_ref_name` on `PullRequestInfo` (types.py)
  -> `pr_is_stacked` in `_build_row_data()` (real.py)
  -> `is_stacked` parameter on `compute_status_indicators()` (lifecycle.py)
  -> `is_stacked` parameter on `_build_indicators()` (lifecycle.py)
```

### MEDIUM Priority

#### 2. Update `github-interface-patterns.md` with three-parser rule and tripwire

**Location:** `docs/learned/architecture/github-interface-patterns.md`
**Action:** UPDATE
**Source:** [PR #7964]

**Draft Content:**

```markdown
## PullRequestInfo Field Addition Protocol

Any new field added to `PullRequestInfo` in
`packages/erk-shared/src/erk_shared/gateway/github/types.py` must be populated in **three**
separate parsers in `packages/erk-shared/src/erk_shared/gateway/github/real.py`:

1. `_parse_pr_from_timeline_event` -- used by issue timeline event queries (GraphQL)
2. `_parse_plan_prs_with_details` -- used by bulk plan PR detail queries (GraphQL)
3. `list_prs` REST path -- used by REST-based PR listing

Missing any one parser causes the field to silently return `None` with no exception raised.
The failure is data-dependent: it only manifests when the specific code path that uses the
missing parser is exercised.

### GraphQL Fragment Divergence Risk

`ISSUE_PR_LINKAGE_FRAGMENT` and `GET_PLAN_PRS_WITH_DETAILS_QUERY` can include different fields.
When adding a field to one, check whether it also needs to be added to the other. Fragment
divergence causes the same conceptual query to return different fields depending on which
code path populates the data.

See `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py` (grep for
`ISSUE_PR_LINKAGE_FRAGMENT`).

### Example: `base_ref_name` (added in PR #7964)

The `base_ref_name: str | None` field was added to `PullRequestInfo` with `baseRefName`
added to both `ISSUE_PR_LINKAGE_FRAGMENT` and `GET_PLAN_PRS_WITH_DETAILS_QUERY`, plus
the REST `list_prs` path. All three parsers were updated in the same PR.
```

#### 3. Update `visual-status-indicators.md` with blocking/informational indicator classification

**Location:** `docs/learned/desktop-dash/visual-status-indicators.md`
**Action:** UPDATE
**Source:** [PR #7964]

**Draft Content:**

```markdown
## Blocking vs. Informational Indicators

Lifecycle indicators are classified as either **blocking** or **informational**:

- **Blocking indicators** (e.g., draft, conflict, unpublished): Prevent the rocket emoji
  from appearing in the implemented stage. When any blocking indicator is present, the
  rocket is suppressed.
- **Informational indicators** (e.g., pancake/stacked): Do NOT prevent the rocket emoji.
  They convey status information without affecting lifecycle progression display.

The mechanism: `has_blocking_indicators = any(i != "<stacked_emoji>" for i in indicators)`.
Future indicator authors adding a new informational indicator must add their emoji to this
exclusion check, or the rocket will never appear for plans with that indicator set.

See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`
(grep for `has_blocking_indicators`).
```

#### 4. Update `github-api-retry-mechanism.md` with two-tier polling strategy

**Location:** `docs/learned/architecture/github-api-retry-mechanism.md`
**Action:** UPDATE
**Source:** [PR #7964]

**Draft Content:**

```markdown
## Workflow Run Polling Strategy

<!-- UPDATE existing polling/backoff section -->

The workflow run polling uses a two-tier backoff strategy:

- **Fast tier**: 5 attempts at 1-second intervals (catches cases where GitHub indexes quickly)
- **Slow tier**: 10 attempts at 2-second intervals (handles eventual consistency delays)
- **Total**: 15 attempts, maximum wait ~25 seconds

This replaced the previous exponential backoff (7 attempts, capped at 8s, max ~36s). The
two-tier approach provides a fast path for the common case while still allowing enough
time for GitHub's eventual consistency.
```

#### 5. Update `planning/lifecycle.md` to mention `is_stacked` as display input

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE
**Source:** [PR #7964]

**Draft Content:**

```markdown
<!-- ADD to the "Display Computation" section -->

### Stacked State

`is_stacked` is an input to `compute_status_indicators()` and `format_lifecycle_with_status()`.
Unlike other display inputs, stacked state is derived from `base_ref_name` on `PullRequestInfo`
(not from plan-header metadata), so it is always current and does not require a lifecycle stage
write point. See `docs/learned/tui/stacked-pr-indicator.md` for the full detection strategy.
```

### LOW Priority

#### 6. Document session discovery branch mismatch behavior

**Location:** `docs/learned/sessions/discovery-fallback.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
<!-- ADD section or update existing content -->

## Branch Matching Behavior

`get-learn-sessions` matches sessions by git branch name. Implementation sessions created
on feature branches (e.g., `plnd/add-stacked-pr-emoji-02-23-0658`) are skipped when
running `/erk:learn` from a stub worktree because the stub branch name
(e.g., `__erk-slot-38-br-stub__`) does not match.

This is expected behavior. The learn session itself is used as a fallback proxy for analysis.
It is not a bug -- it is a design constraint of branch-based session discovery.
```

## Contradiction Resolutions

No genuine contradictions detected. The `get_plan_backend()` references in `docs/learned/planning/draft-pr-plan-backend.md` represent stale documentation (code deleted in PR #7971), not a contradiction with new guidance. This is handled as a Stale Documentation Cleanup item above.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Silent null values from missing PullRequestInfo parser update

**What happened:** Adding `base_ref_name` to `PullRequestInfo` required updating three separate parsers in `real.py`. Missing any one parser would cause the field to silently return `None` on certain code paths, with no exception raised.
**Root cause:** `PullRequestInfo` is populated by three independent parsers (GraphQL timeline, GraphQL details, REST) that do not share a common construction path. There is no compile-time or runtime check that all parsers populate all fields.
**Prevention:** Tripwire on `PullRequestInfo` field additions directing agents to update all three parsers.
**Recommendation:** TRIPWIRE (score 7/10, already captured below)

### 2. GraphQL fragment divergence causing silent data gaps

**What happened:** `baseRefName` needed to be added to `ISSUE_PR_LINKAGE_FRAGMENT` separately from `GET_PLAN_PRS_WITH_DETAILS_QUERY`. The fragment and full query include different fields, so a field added to only one causes data gaps depending on which code path runs.
**Root cause:** GraphQL fragments are reusable components that can diverge from the queries that use them. No tooling enforces field parity between fragment and query.
**Prevention:** Tripwire reminding agents to check both fragment and query when adding fields.
**Recommendation:** TRIPWIRE (score 5/10, already captured below)

### 3. Exponential backoff insufficient for GitHub eventual consistency

**What happened:** The old exponential backoff (7 attempts, capped at 8s) sometimes timed out waiting for GitHub to index workflow runs, while other times the run was found on the first attempt.
**Root cause:** GitHub's workflow run indexing has bimodal latency -- usually fast (under 2s) but occasionally slow (10-20s).
**Prevention:** Two-tier polling strategy documented in `github-api-retry-mechanism.md`.
**Recommendation:** ADD_TO_DOC (captured as documentation item 4 above)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Three-parser PullRequestInfo update rule

**Score:** 7/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2, External tool quirk +1)
**Trigger:** Before adding a field to `PullRequestInfo` in `packages/erk-shared/src/erk_shared/gateway/github/types.py`
**Warning:** Update all three parsers in `real.py`: `_parse_pr_from_timeline_event` (GraphQL timeline), `_parse_plan_prs_with_details` (GraphQL details), AND the REST `list_prs` path. Missing one causes silent `None` values for the new field -- no exception is raised.
**Target doc:** `docs/learned/architecture/github-interface-patterns.md`

This is tripwire-worthy because the failure mode is completely silent. An agent adding a new field to `PullRequestInfo` would naturally update the dataclass and one or two parsers, but nothing in the code structure hints that three separate parsers exist. The field would appear to work in testing (if the test exercises the updated parser path) but fail in production when a different code path populates the data. The cross-cutting nature (three files, two query languages, one REST path) and the silent failure mode make this a strong tripwire candidate.

### 2. GraphQL fragment vs. full query divergence

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2, minus 1 for overlap with three-parser rule)
**Trigger:** Before adding a field to a GraphQL query that also uses fragments
**Warning:** Check whether the field also needs to be added to `ISSUE_PR_LINKAGE_FRAGMENT`. Fragment and full query (`GET_PLAN_PRS_WITH_DETAILS_QUERY`) can diverge silently, causing the field to be populated only on some code paths.
**Target doc:** `docs/learned/architecture/github-interface-patterns.md`

This is related to but distinct from the three-parser rule. Even if an agent remembers to update all three parsers, they might not realize that the GraphQL fragment and full query can include different fields. The failure mode is the same (silent `None` values), but the trigger is different (editing GraphQL queries rather than editing `types.py`).

## Potential Tripwires

Items with score 2-3 that may warrant promotion with additional context:

### 1. Stacked indicator ordering rule

**Score:** 3/10 (Non-obvious +2, Destructive potential +1)
**Notes:** The pancake emoji must be inserted as the first indicator in `_build_indicators()`. Breaking this ordering makes the indicator invisible behind other status markings. However, this applies within a single function with a narrow scope, so it is better documented as an ordering rule note in `stacked-pr-indicator.md` than as a standalone tripwire. If future PRs add more indicators with specific ordering requirements, this could be promoted.

### 2. `has_blocking_indicators` exclusion pattern for informational indicators

**Score:** 3/10 (Non-obvious +2, Destructive potential +1)
**Notes:** Future informational indicators must be excluded from the `has_blocking_indicators` check, or the rocket emoji will never appear for implemented plans with that indicator set. This is a design rule that applies to a medium-frequency action (adding new indicators). It is documented as a design rule in `visual-status-indicators.md` rather than a standalone tripwire. If multiple informational indicators are added and agents keep missing the exclusion, this should be promoted.

### 3. ERK_PLAN_BACKEND default change

**Score:** 3/10 (Non-obvious +2, Destructive potential +1)
**Notes:** The default backend changed from `github` to `draft_pr`. CI environments relying on the old default may produce wrong backend silently. This is largely mitigated by the `draft-pr-plan-backend.md` update (stale documentation cleanup item 1). Document the default explicitly in that doc rather than as a standalone tripwire.
