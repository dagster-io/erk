# Consolidated Documentation Plan

> **Consolidates:** #5662, #5656, #5652, #5648, #5636, #5628

## Source Plans

| # | Title | Items | Status |
|---|-------|-------|--------|
| 5662 | Fix Graphite branch tracking divergence | 5 | Code done (PR #5651), docs missing |
| 5656 | Fix Learn Plan Submission to Stack | 5 | Code done (PR #5655), docs missing |
| 5652 | GitHub API Retry Mechanism Documentation | 9 | Code done (PR #5640), docs missing |
| 5648 | Fix Learn Workflow CI Crash Documentation | 3 | Code done (PR #5646), docs missing |
| 5636 | Model selection for learn workflow | 4 | Partial (2/4 done) |
| 5628 | Complete Branch Operations Extraction | 10 | Code done (PR #5621), 3/10 docs done |

## What Changed Since Original Plans

All 6 plans were created as "learn plans" to document code that was already implemented. The code implementations are complete and merged. Only the documentation work remains.

## Investigation Findings

### Corrections to Original Plans

- **#5662**: Code implementation complete; tripwire about diverged branches still needed
- **#5656**: `get_learn_plan_parent_branch()` function exists with tests; docs missing
- **#5652**: Retry mechanism fully implemented; new doc file never created
- **#5648**: CI detection code exists in learn.md; ci-aware-commands.md never created
- **#5636**: Agent Tier Architecture section already added to learn-workflow.md; 2 sections still missing
- **#5628**: BranchManager and sub-gateways implemented; 7 doc updates missing

### Overlap Analysis

Documentation items cluster into these target files:

| Target File | Items From |
|-------------|-----------|
| `docs/learned/planning/learn-workflow.md` | #5662 (1), #5656 (3), #5648 (1), #5636 (2) |
| `docs/learned/architecture/erk-architecture.md` | #5656 (1), #5628 (1) |
| `docs/learned/architecture/git-graphite-quirks.md` | #5662 (2) |
| `docs/learned/tripwires.md` | #5662 (1), #5652 (4), #5648 (2) |
| `docs/learned/architecture/github-api-retry-mechanism.md` | #5652 (1) - NEW FILE |
| `docs/learned/cli/ci-aware-commands.md` | #5648 (1) - NEW FILE |
| `docs/learned/architecture/gateway-abc-implementation.md` | #5652 (1), #5628 (1) |
| `docs/learned/testing/testing.md` | #5662 (2), #5628 (2) |
| `docs/learned/planning/lifecycle.md` | #5656 (1) |
| `docs/learned/planning/agent-delegation.md` | #5636 (1) |

## Remaining Documentation Items

### HIGH Priority (13 items)

#### 1. Parent Branch Divergence Section _(from #5662)_
- **File**: `docs/learned/architecture/git-graphite-quirks.md`
- **Action**: Add "Parent Branch Divergence Detection" section after "Graphite track_branch Remote Ref Limitation"
- **Content**: Document `_ensure_local_matches_remote()` validation in GraphiteBranchManager

#### 2. Tripwire: Parent Branch Divergence _(from #5662)_
- **File**: `docs/learned/architecture/git-graphite-quirks.md` frontmatter
- **Action**: Add tripwire about calling BranchManager.create_branch() with origin/... refs

#### 3. Learn Plan Parent Branch Stacking _(from #5656)_
- **File**: `docs/learned/planning/learn-workflow.md`
- **Action**: Add section documenting auto-detection, how it works, and fallback behavior

#### 4. Submit Command Learn Plan Behavior _(from #5656)_
- **File**: `docs/learned/planning/lifecycle.md`
- **Action**: Add "Learn Plan Base Branch Selection" subsection to Phase 2

#### 5. NEW: GitHub API Retry Mechanism _(from #5652)_
- **File**: `docs/learned/architecture/github-api-retry-mechanism.md`
- **Action**: CREATE new document with retry patterns, transient error detection, Time injection

#### 6. Tripwire: execute_gh_command without retry _(from #5652)_
- **File**: Source doc frontmatter for `tripwires.md` regeneration
- **Action**: Add critical tripwire about using execute_gh_command_with_retry()

#### 7. Learn Workflow CI Behavior _(from #5648)_
- **File**: `docs/learned/planning/learn-workflow.md`
- **Action**: Add "CI Environment Behavior" section with detection pattern

#### 8. NEW: CI-Aware Commands _(from #5648)_
- **File**: `docs/learned/cli/ci-aware-commands.md`
- **Action**: CREATE new document with CI detection pattern, branching pattern, common pitfalls

#### 9. Tripwires: CI-Aware Commands _(from #5648)_
- **File**: Source doc frontmatter
- **Action**: Add 2 tripwires about user-interactive steps and blocking commands in CI

#### 10. Multi-Tier Agent Orchestration Pattern _(from #5636)_
- **File**: `docs/learned/planning/agent-delegation.md`
- **Action**: Add section explaining the parallel extraction → sequential synthesis pattern

#### 11. Agent Input/Output Formats _(from #5636)_
- **File**: `docs/learned/planning/learn-workflow.md`
- **Action**: Add reference section documenting each agent's input/output format

#### 12. Sub-Gateway Pattern Section _(from #5628)_
- **File**: `docs/learned/architecture/gateway-abc-implementation.md`
- **Action**: Add section documenting GitBranchOps/GraphiteBranchOps extraction pattern

#### 13. Tripwires: Gateway Method Migration _(from #5628)_
- **File**: Already present in tripwires.md (lines 34-38)
- **Status**: ALREADY COMPLETE - no action needed

### MEDIUM Priority (10 items)

#### 14. Branch Divergence Testing Patterns _(from #5662)_
- **File**: `docs/learned/testing/testing.md`
- **Action**: Add section about testing divergence scenarios with FakeGit

#### 15. BranchManager Test Placement _(from #5662)_
- **File**: `docs/learned/testing/testing.md`
- **Action**: Add `tests/unit/branch_manager/` to directory structure

#### 16. get_learn_plan_parent_branch() Documentation _(from #5656)_
- **File**: `docs/learned/planning/learn-workflow.md`
- **Action**: Add "Parent Branch Resolution API" subsection

#### 17. Graceful Branch Fallback Pattern _(from #5656)_
- **File**: `docs/learned/architecture/erk-architecture.md`
- **Action**: Add "Graceful Degradation Patterns" section

#### 18. Time Dependency Injection for Retry _(from #5652)_
- **File**: `docs/learned/architecture/gateway-abc-implementation.md`
- **Action**: Add Time injection section for retry-enabled gateways

#### 19. Subprocess Wrappers Cross-Reference _(from #5652)_
- **File**: `docs/learned/architecture/subprocess-wrappers.md`
- **Action**: Add cross-reference to GitHub retry mechanism

#### 20. GitHub API Rate Limits + Retry Interaction _(from #5652)_
- **File**: `docs/learned/architecture/github-api-rate-limits.md`
- **Action**: Add section clarifying rate limits are NOT retried

#### 21. DryRunGraphite Unwrapping _(from #5628)_
- **File**: `docs/learned/architecture/erk-architecture.md`
- **Action**: Add context.branch_manager property explanation

#### 22. FakeGraphite API Changes _(from #5628)_
- **File**: `docs/learned/testing/testing.md`
- **Action**: Document `create_linked_branch_ops()` pattern

#### 23. Query/Mutation Split Rationale _(from #5628)_
- **File**: `docs/learned/architecture/gateway-abc-implementation.md`
- **Action**: Explain why mutations extracted to sub-gateways

### LOW Priority (5 items)

#### 24. Learn Workflow Simplifications _(from #5662)_
- **File**: `docs/learned/planning/learn-workflow.md`
- **Action**: Note about removed validation steps

#### 25. Learn Plan Branch Hierarchy _(from #5656)_
- **File**: `docs/learned/planning/learn-workflow.md`
- **Action**: Add visual hierarchy diagram for branch stacking

#### 26. Tripwire: Type narrowing with with_retries _(from #5652)_
- **File**: Source doc frontmatter
- **Action**: Add tripwire about isinstance() after RetriesExhausted check

#### 27. Stateless File-Based Composition _(from #5636)_
- **File**: `docs/learned/planning/learn-workflow.md`
- **Action**: Add rationale subsection

#### 28. Branch Restoration Note _(from #5628)_
- **File**: `docs/learned/architecture/git-graphite-quirks.md`
- **Action**: Add note about branch restoration after Graphite tracking

## Attribution

| Source Plan | Items in Consolidated Plan |
|-------------|---------------------------|
| #5662 | Items 1, 2, 14, 15, 24 |
| #5656 | Items 3, 4, 16, 17, 25 |
| #5652 | Items 5, 6, 18, 19, 20, 26 |
| #5648 | Items 7, 8, 9 |
| #5636 | Items 10, 11, 27 |
| #5628 | Items 12, 13, 21, 22, 23, 28 |

## Implementation Steps

### Phase 1: Create New Files
1. Create `docs/learned/architecture/github-api-retry-mechanism.md` (Item 5)
2. Create `docs/learned/cli/ci-aware-commands.md` (Item 8)

### Phase 2: Update Planning Docs
3. Update `docs/learned/planning/learn-workflow.md` with Items 3, 7, 11, 16, 24, 25, 27
4. Update `docs/learned/planning/lifecycle.md` with Item 4
5. Update `docs/learned/planning/agent-delegation.md` with Item 10

### Phase 3: Update Architecture Docs
6. Update `docs/learned/architecture/git-graphite-quirks.md` with Items 1, 2, 28
7. Update `docs/learned/architecture/gateway-abc-implementation.md` with Items 12, 18, 23
8. Update `docs/learned/architecture/erk-architecture.md` with Items 17, 21
9. Update `docs/learned/architecture/subprocess-wrappers.md` with Item 19
10. Update `docs/learned/architecture/github-api-rate-limits.md` with Item 20

### Phase 4: Update Testing Docs
11. Update `docs/learned/testing/testing.md` with Items 14, 15, 22

### Phase 5: Regenerate Tripwires
12. Run `erk docs sync` to regenerate tripwires.md from source frontmatter

## Verification

1. Run `erk docs sync` to validate frontmatter and regenerate tripwires
2. Verify all new tripwires appear in `docs/learned/tripwires.md`
3. Check cross-references between documents are valid
4. Run `make format` on any modified markdown files

## Critical Files

### Files to Create
- `docs/learned/architecture/github-api-retry-mechanism.md`
- `docs/learned/cli/ci-aware-commands.md`

### Files to Update
- `docs/learned/planning/learn-workflow.md`
- `docs/learned/planning/lifecycle.md`
- `docs/learned/planning/agent-delegation.md`
- `docs/learned/architecture/git-graphite-quirks.md`
- `docs/learned/architecture/gateway-abc-implementation.md`
- `docs/learned/architecture/erk-architecture.md`
- `docs/learned/architecture/subprocess-wrappers.md`
- `docs/learned/architecture/github-api-rate-limits.md`
- `docs/learned/testing/testing.md`