# Plan: Consolidated Feb 25-26 Learn Session Documentation

> **Consolidates:** #8272, #8268, #8264, #8262, #8260, #8257, #8256, #8253, #8250, #8249, #8246, #8233, #8228, #8224, #8221, #8219, #8216, #8214, #8207, #8206

## Context

19 erk-learn documentation plans accumulated from Feb 25-26 implementation sessions. All underlying PRs are merged (except #8214 which has a branch). Investigation found ~200 documentation items across all plans, heavily overlapping. This consolidated plan deduplicates and prioritizes into an actionable sequence.

**Key finding:** Most implementation work is complete. The gap is documentation capture - tripwires, patterns, and stale reference cleanup.

## Source Plans

| # | Title | Items | Status |
|---|-------|-------|--------|
| 8272 | Delete -t/--tmux from codespace connect | 0 | SKIP (zero docs needed) |
| 8268 | PR feedback classifier performance | 17 | All code merged |
| 8264 | RoadmapNode/ObjectiveNode plan field | 12 | All code merged |
| 8262 | Dead code elimination after pr sync | 8 | All code merged |
| 8260 | Consolidate plan saving | 11 | All code merged |
| 8257 | Delete erk pr sync | 11 | All code merged |
| 8256 | Testing infrastructure gaps | 16 | All code merged |
| 8253 | CLI consolidation (plan -> pr) | 11 | All code merged |
| 8250 | Tmux session persistence | 18 | All code merged |
| 8249 | retrack_branch on BranchManager | 10 | All code merged |
| 8246 | PR checkout simplification | 15 | All code merged |
| 8233 | Delete GitHubPlanStore/PlanStore ABC | 14 | All code merged |
| 8228 | PR sync resilience | 8 | OBSOLETE (sync deleted) |
| 8224 | HTTP-accelerated Plans tab | 26 | All code merged |
| 8221 | Remove plan CLI group | 11 | All code merged |
| 8219 | Fix TUI dispatch command | 5 | All code merged |
| 8216 | Fix learn PRs in Planned PRs tab | 11 | All code merged |
| 8214 | Performance optimization docs | 16 | Branch only |
| 8207 | PlanDataTable in ObjectivePlansScreen | 12 | All code merged |
| 8206 | erk-planned-pr label scheme | 28 | All code merged |

## What Changed Since Original Plans

- `erk pr sync` fully deleted (PR #8254) - makes #8228 documentation about sync_idempotent() OBSOLETE
- All plan CLI commands moved under `erk pr` (PR #8226) - docs still reference old paths
- PlanStore ABC and GitHubPlanStore deleted (PR #8210) - docs still reference them
- PlannedPRBackend is now sole backend with 3-arg constructor
- Two-label scheme (erk-planned-pr + type-specific) fully operational

## Investigation Findings

### Corrections to Original Plans
- **#8228**: Plan proposes documenting `sync_idempotent()` - method was DELETED in PR #8254. Only the general convenience method pattern (via `squash_branch_idempotent()`) is still relevant.
- **#8264**: Plan proposes re-adding `plan` field - the field was intentionally kept out. Only `pr` field exists on ObjectiveNode/RoadmapNode.
- **#8272**: Plan proposes documentation items - investigation found ZERO new docs needed (existing feature-removal-checklist.md covers the pattern).

### Overlap Analysis
- **Post-refactoring audit pattern**: Plans #8260, #8253, #8221 all identify stale references after refactoring - merged into single doc
- **Command deletion patterns**: Plans #8257, #8246 both propose vestigial feature detection - merged
- **Label filtering**: Plans #8216, #8206, #8224 all touch label-based filtering - merged into label scheme doc
- **Backend constructor**: Plans #8256, #8206 both identify PlannedPRBackend constructor issues - merged into single tripwire
- **Testing patterns**: Plans #8256, #8249, #8233 all discuss test infrastructure - merged

## Implementation Steps

### Phase 1: Fix Broken Documentation (prevents agent errors NOW)

#### Step 1.1: Delete phantom `plan` field references from objective docs
_(from #8264)_

**Files to modify:**
- `docs/learned/objectives/dependency-graph.md` - Remove line 28 phantom `plan` field
- `docs/learned/objectives/roadmap-parser-api.md` - Remove line 83 `plan` field description
- `docs/learned/objectives/roadmap-format-versioning.md` - Remove lines 24, 67 phantom `plan` field

**Evidence:** ObjectiveNode/RoadmapNode in `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py` (lines 40-49) and `roadmap.py` (lines 30-38) have NO `plan` field - only `pr`. Note: PR #8209 commit message claims "Re-add plan field" but the actual diff did NOT add the field - it only added `compute_objective_head_state()` and display fixes.

**Verification:** `grep -r "plan.*field" docs/learned/objectives/` returns no phantom references

#### Step 1.2: Fix phantom CLI command references
_(from #8219, #8221, #8253)_

**Files to modify:**
- `docs/learned/cli/command-organization.md` (lines 59-66) - Change `erk plan submit` to `erk pr dispatch`
- `docs/learned/glossary.md` - Remove `erk plan learn complete` entry
- `docs/learned/architecture/markers.md` - Change 2 refs from `erk plan learn` to `erk learn`

**Evidence:** `src/erk/cli/commands/pr/dispatch_cmd.py` is actual command. No `erk plan` group exists.

**Verification:** `grep -r "erk plan " docs/learned/ | grep -v "erk-plan"` returns no phantom command references

#### Step 1.3: Fix view-switching label documentation contradiction
_(from #8216)_

**File:** `docs/learned/tui/view-switching.md`

**Fix:** Remove claim that "Plans and Learn views share the same API label". Clarify:
- Plans view queries with `labels=("erk-plan",)`
- Learn view queries with `labels=("erk-learn",)`
- Both share BASE label `erk-planned-pr` but use DIFFERENT type labels

**Evidence:** `src/erk/tui/views/types.py` ViewConfig definitions show different labels per view.

#### Step 1.4: Clean up stale backend references
_(from #8233)_

**Files to modify:**
- `docs/learned/architecture/erk-architecture.md` (lines 362-371) - Remove PlanStore vs PlanBackend distinction
- `docs/learned/architecture/gateway-vs-backend.md` - Replace GitHubPlanStore examples with PlannedPRBackend
- Consolidate `docs/learned/planning/plan-backend-migration.md` and `docs/learned/architecture/plan-backend-migration.md` into single file

**Evidence:** PlanBackend is sole ABC at `packages/erk-shared/src/erk_shared/plan_store/backend.py:51`. GitHubPlanStore deleted.

### Phase 2: Critical Tripwires (highest prevention value)

#### Step 2.1: Create GitHub GraphQL AND-logic tripwire
_(from #8206 - score 8/10, highest priority tripwire)_

**File:** NEW `docs/learned/architecture/github-graphql-label-semantics.md`

**Content:**
- GitHub GraphQL uses AND semantics for label filters (not OR)
- Silent filtering: No error, just fewer results than expected
- Decision: Query by type-specific labels only, not base label
- Impact: Affects all `gh api graphql` calls with label filters

**Also add tripwire entry to:** `docs/learned/architecture/tripwires.md`

#### Step 2.2: Add PlannedPRBackend constructor tripwire
_(from #8256 - score 6/10, 7+ violations observed)_

**Add to:** `docs/learned/architecture/tripwires.md` and `docs/learned/testing/tripwires.md`

**Content:** PlannedPRBackend now requires 3 args (github_gateway, http_client, repo_full_name), not single gateway arg. 7+ PR review violations from agents using old signature.

**Evidence:** `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py` constructor

#### Step 2.3: Add routing inversion and multi-label deduplication tripwires
_(from #8206 - scores 7/10 and 6/10)_

**Add to:** `docs/learned/architecture/tripwires.md`

**Content:**
- Routing: Check exceptions first (erk-objective), route everything else to default service
- Deduplication: GitHub queries return duplicates when items match all labels; must deduplicate by ID before DataTable.populate()

#### Step 2.4: Add type narrowing tripwires
_(from #8268 - scores 6/10, 5/10)_

**Add to:** `docs/learned/architecture/tripwires.md`

**Content:**
- Protocol isinstance checks don't narrow union types in Python type checkers
- Use `assert_never()` or `assert False` after NoReturn calls for type narrowing
- NonIdealState.ensure() pattern replaces verbose `_ensure_*` helper functions

#### Step 2.5: Add post-refactoring documentation audit tripwire
_(from #8260, #8253 - score 5/10, 64% review violations from stale docs)_

**File:** NEW `docs/learned/refactoring/post-refactor-documentation-audit.md`

**Content:** 5-step checklist: grep docs/learned/ for old names, verify command references, check tripwire entries, update glossary, run `erk docs sync`

**Also add tripwire to:** `docs/learned/refactoring/tripwires.md`

#### Step 2.6: Add stale documentation reference tripwire
_(from #8221 - score 6/10)_

**Add to:** `docs/learned/cli/tripwires.md`

**Content:** Before removing a CLI command or group, search docs/learned/ for all references. Post-removal grep verification is mandatory.

#### Step 2.7: Add HEREDOC JSON piping tripwire
_(from #8260, #8253 - score 6/10)_

**Add to:** `docs/learned/cli/tripwires.md` or NEW `docs/learned/pr-operations/json-piping-patterns.md`

**Content:** Use HEREDOC for JSON in erk exec commands to prevent silent parse failures from shell escaping.

### Phase 3: High-Impact New Documentation

#### Step 3.1: Create codespace tmux persistence doc
_(from #8250 - 18 items, core new feature)_

**File:** NEW `docs/learned/integrations/codespace-tmux-persistence.md`

**Content:**
- Core pattern: Bootstrap outside tmux, session inside tmux
- Session naming: Deterministic for plans, TTY-derived for interactive
- TERM=xterm-256color requirement for remote tmux
- Session cleanup guidance
- CLI flag cascading (--session implies --tmux)

**Evidence:** `src/erk/cli/commands/codespace/connect_cmd.py`, `codespace_run.py`

#### Step 3.2: Create command deletion patterns doc
_(from #8257, #8262 - overlapping items merged)_

**File:** NEW `docs/learned/cli/command-deletion-patterns.md`

**Content:**
- 4-phase deletion: file removal, registration removal, doc updates, verification
- Dead type cleanup: multiplicative cleanup pattern (N types * M variants)
- Integration test co-evolution: grep tests/integration/ before deleting gateway methods
- Vestigial feature detection: 3-signal pattern (docstring admits redundancy + zero programmatic invocations + docs list alternatives)

**Evidence:** PR #8245 (sync deletion, 373 lines), PR #8254 (dead code, 6 types * 3 variants deleted)

#### Step 3.3: Create label assignment scheme doc
_(from #8206, #8216 - overlapping label documentation merged)_

**File:** UPDATE `docs/learned/planning/planned-pr-backend.md` or NEW `docs/learned/planning/label-scheme.md`

**Content:**
- Two-label scheme: `erk-planned-pr` (base) + type-specific (`erk-plan`, `erk-learn`)
- Label assignment logic in PlannedPRBackend.create_plan()
- Label backfill timestamp side-effects (changes updated_at)
- Defense-in-depth filtering: server-side label filter + client-side exclude_labels

#### Step 3.4: Create HTTP-accelerated plan refresh doc
_(from #8224 - largest single plan, 26 items)_

**File:** NEW `docs/learned/architecture/http-accelerated-plan-refresh.md`

**Content:**
- Dual-path architecture: CLI subprocess path vs HTTP direct API path
- HttpClient ABC extensions: `get_list()`, `graphql()`, `supports_direct_api`
- 5-place gateway implementation pattern (abc, real, fake, dry_run, printing)
- PR data parsing extraction to shared module
- Service parameter threading pattern (24+ call sites)

**Evidence:** `src/erk/core/services/plan_list_service.py` lines 131-150, `packages/erk-shared/src/erk_shared/gateway/http/abc.py`

#### Step 3.5: Create FakeGitHub mutation tracking reference
_(from #8256)_

**File:** NEW `docs/learned/testing/fake-github-api-reference.md`

**Content:**
- FakeGitHub.create_pr() auto-registration in _pr_details
- Mutation tracking API for test assertions
- context_for_test() parameter naming conventions
- Test helper function patterns

#### Step 3.6: Update BranchManager documentation
_(from #8249)_

**File:** UPDATE existing BranchManager docs (identify correct file)

**Content:**
- Add retrack_branch() method documentation
- Document 4-file pattern (no dry_run/printing for composition abstractions)
- Abstraction value: simplifies call site from ctx.graphite_branch_ops to ctx.branch_manager

#### Step 3.7: Create modal widget embedding pattern doc
_(from #8207)_

**File:** NEW `docs/learned/tui/modal-widget-embedding.md`

**Content:**
- Pattern for reusing PlanDataTable in ObjectivePlansScreen modal
- PlanDataTable ID limitation (doesn't support id= kwarg)
- Null safety for optional gateway fields
- Event handler testing patterns in Textual

**Evidence:** `src/erk/tui/screens/objective_plans_screen.py`

### Phase 4: Medium Priority Updates

#### Step 4.1: Add performance optimization tripwires
_(from #8214, #8268)_

**Add to:** `docs/learned/architecture/tripwires.md`

**Content:**
- ThreadPoolExecutor for parallel I/O in exec scripts
- Subprocess overhead: 200-300ms per gh api call
- Batch operations pattern: Replace N subprocess calls with single command (30-100x improvement)
- git for-each-ref batching

#### Step 4.2: Update ABC convenience methods doc
_(from #8228, but sync_idempotent is OBSOLETE)_

**File:** `docs/learned/architecture/abc-convenience-methods.md`

**Content:** Add note that sync_idempotent() was deleted as dead code. Pattern still valid via squash_branch_idempotent() example.

#### Step 4.3: Update PR checkout workflow docs
_(from #8246)_

**File:** UPDATE `docs/learned/cli/checkout-helpers.md`

**Content:**
- PR checkout is now self-sufficient (fetches and updates local branch)
- No longer requires separate erk pr sync step
- _fetch_and_update_branch() helper function

#### Step 4.4: Create exec script performance pattern doc
_(from #8268)_

**File:** NEW or UPDATE `docs/learned/architecture/exec-script-patterns.md`

**Content:**
- NonIdealState.ensure() replaces _ensure_* helpers
- Combined commands reduce overhead (15-25s to 5-8s)
- @handle_non_ideal_exit decorator pattern

### Phase 5: Skill Fix (from investigation)

#### Step 5.1: Fix replan skill validation for learn plans

The `/erk:replan` skill validates for `erk-plan` label, but learn plans correctly use `erk-learn` + `erk-pr` without `erk-plan`. Update the validation in the replan skill to accept either `erk-plan` OR `erk-learn` labeled issues.

**File:** `.claude/skills/erk-replan/skill.md` (or wherever the replan skill is defined)

Also: Remove incorrect `erk-plan` label from issues #8216, #8214, #8207 (learn plans that shouldn't have it).

## Attribution

| Source Plans | Steps |
|---|---|
| #8264 | 1.1, 1.4 |
| #8219, #8221, #8253 | 1.2 |
| #8216 | 1.3, 3.3 |
| #8233 | 1.4 |
| #8206 | 2.1, 2.3, 3.3 |
| #8256 | 2.2, 3.5 |
| #8268 | 2.4, 4.4 |
| #8260, #8253 | 2.5, 2.7 |
| #8221 | 2.6 |
| #8250 | 3.1 |
| #8257, #8262 | 3.2 |
| #8224 | 3.4 |
| #8249 | 3.6 |
| #8207 | 3.7 |
| #8214 | 4.1 |
| #8228 | 4.2 |
| #8246 | 4.3 |
| #8272 | (none - zero docs needed) |

## Post-Plan Steps (after implementation)

1. **Save plan to GitHub** with `--plan-type=learn` flag (since all source plans are erk-learn)
2. **Add `erk-consolidated` label** to the new plan issue
3. **Close all 19 source issues** with comment linking to consolidated plan (skip #8272 which needs zero docs - close with "Zero docs needed per investigation")
4. **Post investigation findings** to each original issue as a comment (summary of what was implemented vs obsolete)

## Verification

After implementation:
1. `grep -r "erk plan submit\|erk plan list\|erk plan dispatch" docs/learned/` - should return zero matches
2. `grep -r "plan.*field" docs/learned/objectives/` - should return no phantom references to plan field on RoadmapNode/ObjectiveNode
3. `grep -r "GitHubPlanStore\|PlanStore ABC" docs/learned/` - should return no stale references
4. `grep -r "erk plan learn complete" docs/learned/` - should return zero matches
5. Run `erk docs sync` to regenerate index files
6. Verify tripwire counts increased in `docs/learned/tripwires-index.md` after sync
