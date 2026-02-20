<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary>plan-header</summary>

```yaml

schema_version: '2'
created_at: '2026-02-20T11:42:29.228540+00:00'
created_by: schrockn
plan_comment_id: null
last_dispatched_run_id: '22232708786'
last_dispatched_node_id: WFR_kwLOPxC3hc8AAAAFLSw2sg
last_dispatched_at: '2026-02-20T16:45:17.062565+00:00'
last_local_impl_at: null
last_local_impl_event: null
last_local_impl_session: null
last_local_impl_user: null
last_remote_impl_at: null
last_remote_impl_run_id: null
last_remote_impl_session_id: null
branch_name: plan-restore-missing-pr-status-02-20-1142
created_from_session: 9522a511-1a9e-47dc-8f0e-92f64141a4b0
lifecycle_stage: planned

```

</details>
<!-- /erk:metadata-block:plan-header -->


---

<details>
<summary>original-plan</summary>

# Restore Missing PR Status Information in Draft PR Dashboard

## Context

When erk switched from issue-based plans to draft-PR-based plans, the TUI dashboard lost visibility into critical PR health information. The root cause: in issue mode, a separate `pr` column displayed rich status emoji (`#123 👀💥`). In draft_pr mode, the plan IS the PR, so `show_pr_column=False` hides that column — and with it, the merge conflict indicator and PR state emoji.

PR #7618 has `mergeable: "CONFLICTING"` on GitHub, but the dashboard shows no indication of this.

## What Was Dropped

### 1. Merge conflict indicator (CRITICAL)
- **Old**: `pr` column showed `#123 👀💥` — the 💥 emoji indicated `CONFLICTING` status
- **Now**: Hidden. The data IS fetched (`mergeable` in GraphQL, `has_conflicts` on `PullRequestInfo`), `get_pr_status_emoji()` computes the emoji, but `show_pr_column=False` means it's never rendered
- **Impact**: Can't tell if a PR needs rebase before merge

### 2. PR state emoji (MODERATE)
- **Old**: `pr` column showed 🚧 (draft), 👀 (open/published), 🎉 (merged), ⛔ (closed)
- **Now**: Replaced by `stage` column text ("planned", "review", "merged", "closed") — functionally equivalent but less scannable. Note: `stage` is based on lifecycle metadata, not actual GitHub PR state, so they can diverge.

## What Was Never Available But Could Be Useful

### 3. Review decision (VALUABLE)
- `reviewDecision` is NOT in the GraphQL query at all
- Values: `APPROVED`, `CHANGES_REQUESTED`, `REVIEW_REQUIRED`, or null
- During `review` stage, this is critical — you want to know at a glance if your PR has been approved or has changes requested
- Currently the only proxy is the `comments` column (resolved/total threads)

### 4. merge_state_status (LOW VALUE)
- `mergeStateStatus` (CLEAN/DIRTY/BLOCKED/UNSTABLE) is fetched in `PRDetails` but not propagated to `PullRequestInfo` or displayed
- Overlaps with `has_conflicts` + `checks_passing` — low incremental value

### 5. PR size / additions+deletions (NICE-TO-HAVE)
- Not fetched. Would help reviewer triage but adds column bloat.

## What Each Lifecycle Stage Needs

| Stage | Conflicts | Review Decision | Checks | Comments |
|---|---|---|---|---|
| planned | - | - | - | - |
| implementing | matters | - | - | - |
| review | **critical** | **critical** | matters | matters |
| merged | - | - | - | - |

## Proposed Changes

### Approach: Enrich the `stage` column with status indicators

Append emoji indicators to the `stage` text when they're relevant. This keeps column count unchanged and puts status where the eye already goes for "what's happening with this PR?"

Examples:
- `review` — no issues
- `review 💥` — has merge conflicts
- `review ✔` — approved
- `review ❌` — changes requested
- `review 💥 ❌` — conflicts AND changes requested
- `implementing 💥` — conflicts during implementation

### Implementation

1. **Add `reviewDecision` to GraphQL queries**
   - `GET_PLAN_PRS_WITH_DETAILS_QUERY` in `graphql_queries.py`
   - `GET_ISSUES_WITH_PR_LINKAGES_QUERY` (for consistency)

2. **Add `review_decision: str | None = None` to `PullRequestInfo`**
   - `packages/erk-shared/src/erk_shared/gateway/github/types.py`

3. **Parse `reviewDecision` in GraphQL response parsers**
   - `packages/erk-shared/src/erk_shared/gateway/github/real.py` — `_parse_plan_prs_with_details`, `_parse_issues_with_pr_linkages`

4. **Add `has_conflicts` and `review_decision` to `PlanRowData`**
   - `src/erk/tui/data/types.py` — new fields with `None` defaults

5. **Create `format_lifecycle_with_status()` in `lifecycle.py`**
   - Takes lifecycle display string + has_conflicts + review_decision
   - Appends indicators only for relevant stages (implementing, review)
   - Inserts indicators inside Rich markup tags so they inherit color

6. **Wire up in `_build_row_data()`**
   - `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`
   - Extract `has_conflicts`/`review_decision` from `selected_pr`
   - Apply `format_lifecycle_with_status()` after computing lifecycle display

7. **Update test helpers and write tests**
   - Update `make_plan_row()` with new params
   - Test `format_lifecycle_with_status()` for each stage + indicator combination
   - Verify TUI renders enriched stage text correctly

### Key Files
- `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py` — add `reviewDecision`
- `packages/erk-shared/src/erk_shared/gateway/github/types.py` — add field to `PullRequestInfo`
- `packages/erk-shared/src/erk_shared/gateway/github/real.py` — parse new field
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py` — new `format_lifecycle_with_status()`
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` — wire up
- `src/erk/tui/data/types.py` — add fields to `PlanRowData`

## Verification
1. Run `erk dash -i` in draft_pr mode
2. Verify PR #7618 (or any PR with merge conflicts) shows `review 💥` in stage column
3. Verify approved PRs show `review ✔`
4. Verify clean PRs still show just `review`
5. Run tests: `make fast-ci`


</details>
---


To checkout this PR in a fresh worktree and environment locally, run:

```
source "$(erk pr checkout 7662 --script)" && erk pr sync --dangerous
```
