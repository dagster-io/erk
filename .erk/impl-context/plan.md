# Plan: Consolidated Documentation for Feb 21 Learn Sessions (Batch 2)

> **Consolidates:** #7776, #7770, #7769, #7766, #7764

## Context

Five erk-learn plans were generated from implementation sessions on Feb 21, 2026. Each plan captures documentation gaps and tripwire candidates discovered during implementation work. The underlying code changes (PRs #7754, #7756, #7757, #7762, #7705) are all merged. This plan consolidates the remaining documentation work, focusing on the highest-impact items.

## Source Plans

| #    | Title                                                   | Items | Documented | Remaining |
| ---- | ------------------------------------------------------- | ----- | ---------- | --------- |
| 7776 | Replace session gist archival with branch-based storage | 26    | ~10%       | ~23       |
| 7769 | Consolidate draft-PR workflow docs / branch naming      | 14    | ~40%       | ~8        |
| 7770 | Learn skill draft PR vs issue display                   | 6     | ~60%       | ~3        |
| 7766 | Lazy tip sync for worktree pool                         | 8     | ~25%       | ~6        |
| 7764 | Draft PR plan list label duplication                    | 3     | 0%         | 3         |

## Investigation Findings

### Corrections to Original Plans

- **#7776**: `docs/learned/sessions/lifecycle.md` lines 47-53 still describe gist-based persistence as current — must be rewritten to reflect branch-based storage
- **#7769**: Plan title says "standardize from slash to hyphen" but code uses `planned/` (slash) consistently — this was documentation consolidation only, not a code change
- **#7770**: Items #3 and #6 are already documented in `draft-pr-learn-pipeline.md` and `backend-aware-commands.md` respectively
- **#7766**: All assumptions verified correct; `slot-pool-architecture.md` exists but has no mention of the transparent sync behavior
- **#7764**: All assumptions verified correct; 0% implemented

### Overlap Analysis

- **Backend-aware display**: #7770 and #7766 both deal with backend-conditional behavior (CLI vs TUI). Merged into single CLI pattern doc (Step 5)
- **Tripwire additions**: Multiple plans add tripwires to the same files — batched by target file
- **Branch naming**: #7776 and #7769 both touch branch naming docs — merged into single fix (Step 2)

## Implementation Steps

### CRITICAL: Fix Stale Documentation

#### Step 1: Rewrite session lifecycle gist references _(from #7776)_

**File:** `docs/learned/sessions/lifecycle.md`

- Rewrite "Why Gist-Based Persistence Exists" section (lines 47-53) to "Why Branch-Based Persistence Exists"
- Update content to describe `session/{plan_id}` branch storage mechanism
- Remove/update any other gist references in the file
- **Source:** PR #7757 replaced gist archival with branch-based storage (commit c7f936340)
- **Verification:** No references to gist-based session storage remain as "current" system

#### Step 2: Fix branch naming inconsistency _(from #7769)_

**File:** `docs/learned/planning/branch-name-inference.md`

- Line 6: Change `plan-` prefix reference to `planned/` to match actual code
- Scan rest of file for any `plan-` vs `planned/` inconsistencies
- **Source:** Code in `docs/learned/erk/branch-naming.md` lines 50-62 confirms `planned/` (slash) prefix
- **Verification:** All branch naming references consistent across docs

### HIGH: Missing Documentation for Implemented Features

#### Step 3: Create lazy pool sync pattern doc _(from #7766)_

**File:** `docs/learned/architecture/slot-pool-state-sync.md` (NEW)

- Document the lazy sync algorithm from PR #7756
- Cover: sync timing (runs after pool load, before allocation), edge cases, I/O optimization (mtime preservation when no changes)
- Reference: `src/erk/core/worktree_pool.py` for implementation details
- **Verification:** Document accurately describes the sync flow in the source code

#### Step 4: Update slot pool architecture doc _(from #7766)_

**File:** `docs/learned/erk/slot-pool-architecture.md`

- Add section on transparent state correction behavior from PR #7756
- Document: pool treats manual `git checkout`/`gt create` as valid, sync corrects mismatches silently
- **Verification:** Section reflects actual behavior in `worktree_pool.py`

#### Step 5: Create CLI backend-aware display pattern doc _(from #7770, #7766)_

**File:** `docs/learned/cli/backend-aware-display.md` (NEW)

- Document pattern for CLI commands that need to route behavior based on `plan_backend`
- Cover: `gh issue view` vs `gh pr view` routing, "draft PR" vs "issue" terminology, `ctx.plan_backend` usage
- Reference existing TUI pattern: `docs/learned/tui/backend-aware-commands.md`
- **Source:** Learn skill implementation in `src/erk/cli/commands/learn/learn_cmd.py`
- **Verification:** Pattern matches actual usage in learn_cmd.py

#### Step 6: Update draft-pr-plan-backend.md _(from #7764)_

**File:** `docs/learned/planning/draft-pr-plan-backend.md`

- Add "Implementation Setup and .erk/impl-context/ Cleanup" section
- Document: cleanup pattern, idempotency considerations, rebase conflict handling
- **Source:** PR #7762 implementation insights
- **Verification:** New section aligns with actual cleanup flow

### MEDIUM: Tripwire Additions (batched by target file)

#### Step 7: Add tripwires to `docs/learned/architecture/tripwires.md` _(from #7776, #7766)_

Add these tripwires:

1. **Sync before allocation** (score 8-9/10) — Pool sync must run BEFORE `find_branch_assignment` call; silent bugs if skipped _(from #7766)_
2. **macOS sed syntax** (score 4/10) — macOS sed requires `sed -i ''` vs Linux `sed -i` _(from #7776)_
3. **Stash side effects on code execution** (score 4/10) — `git stash` changes working tree state which affects running processes _(from #7776)_

**Verification:** Run `erk docs sync` after editing to update tripwire counts

#### Step 8: Add tripwires to `docs/learned/planning/tripwires.md` _(from #7776, #7764)_

Add these tripwires:

1. **Dual backend service consistency** (score 6/10) — `RealPlanListService` and `DraftPRPlanListService` must handle parameters identically; interface contracts not enforced by type system _(from #7764)_
2. **Git pull --rebase after impl-context cleanup** (score 4/10) — Required after cleanup commits to avoid merge conflicts _(from #7776)_
3. **GitHub CLI routing for plan backends** — Using `gh issue view` on a draft-PR plan produces confusing 404; route to `gh pr view` based on backend _(from #7770)_

**Verification:** Run `erk docs sync` after editing to update tripwire counts

#### Step 9: Add tripwires to `docs/learned/ci/tripwires.md` _(from #7764)_

Add:

1. **Git rebase modify/delete conflict resolution** (score 5/10) — In rebase, "them" = upstream (opposite to merge); use `git rm` for conflicted staged files _(from #7764)_

**Verification:** Run `erk docs sync` after editing to update tripwire counts

#### Step 10: Add tripwire to `docs/learned/erk/tripwires.md` _(from #7769)_

Add:

1. **Graphite cache mismatch after raw git** (score 7/10) — Running raw git commands (checkout, branch) without `gt track` causes Graphite cache to diverge from actual branch state _(from #7769)_

**Verification:** Run `erk docs sync` after editing to update tripwire counts

### LOW PRIORITY: Deferred Items

These items from the source plans are deferred as lower impact:

- Schema migration pattern doc (`docs/learned/architecture/schema-migrations.md`) _(from #7776)_
- PR feedback workflow 5-phase structure _(from #7769)_
- Subagent isolation via Task tool _(from #7769)_
- False positive detection procedure _(from #7769)_
- Silent command verification pattern _(from #7769)_
- Plan-save output JSON schema doc _(from #7770)_
- "Branch tip" vs "stack tip" glossary entries _(from #7766)_
- Gist-related doc deprecation notices _(from #7776)_
- Prettier version consistency tripwire _(from #7776)_
- Git stash pattern tripwire _(from #7776)_
- I/O optimization test patterns _(from #7766)_
- FakeGit API documentation _(from #7776)_
- Discriminated union field migration pattern _(from #7776)_
- Gateway sub-gateway discovery pattern _(from #7776)_

## Attribution

Items by source:

- **#7776**: Steps 1, 2 (partial), 7 (items 2-3), 8 (item 2)
- **#7769**: Steps 2, 10
- **#7770**: Steps 5, 8 (item 3)
- **#7766**: Steps 3, 4, 7 (item 1)
- **#7764**: Steps 6, 8 (item 1), 9

## Verification

After all steps:

1. Run `erk docs sync` to regenerate tripwire counts and index
2. Run `make fast-ci` to verify no formatting/lint issues
3. Grep `docs/learned/` for stale gist references (should only appear in historical/reference context, not as "current" system)
4. Verify new files have correct frontmatter format
