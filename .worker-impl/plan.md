# Plan: Consolidated Documentation from Learn Plans #6557, #6556, #6554, #6550, #6549, #6547, #6542

> **Consolidates:** #6557, #6556, #6554, #6550, #6549, #6547, #6542

## Source Plans

| #    | Title                                                              | Items Merged | Code Status      |
| ---- | ------------------------------------------------------------------ | ------------ | ---------------- |
| 6557 | Fix Graphite tracking divergence after commit amend in pr-submit   | 4 items      | MERGED (30f7a7a) |
| 6556 | Fix Objective Roadmap Status Display (#6551)                       | 8 items      | MERGED (4090e6d) |
| 6554 | Optimize objective-update-with-landed-pr (4→2 turns, Haiku)       | 10 items     | Phase 1 MERGED, Phase 2 on branch |
| 6550 | Add Right-Click Context Menu to erkdesk                            | 11 items     | On branch (not merged) |
| 6549 | Add Streaming Log Panel for Action Buttons                         | 8 items      | MERGED (9c9c17f) |
| 6547 | Optimize objective-update-with-landed-pr (Haiku delegation)        | 10 items     | On branch P6547 |
| 6542 | Add contextual action toolbar to erkdesk dashboard                 | 10 items     | MERGED (ce10753) |

## What Changed Since Original Plans

- PR #6532 (action toolbar) and #6541 (streaming log panel) both merged to master
- PR #6544 (Haiku delegation Phase 2) and #6548 (documentation from #6547) are open with CI passing
- Context menu feature (#6550) remains on unmerged branch
- Previous consolidation (#6545) already merged documentation from earlier learn plans

## Investigation Findings

### Overlap Analysis

1. **#6554 and #6547 are near-duplicates** - both cover Haiku delegation optimization. #6547 has ALL docs implemented on branch P6547 (PR #6548). #6554 falsely claims docs are complete but they're not on master. **Merge strategy**: Use #6547's implemented docs (on branch), skip #6554's redundant items.

2. **#6542 and #6549 share erkdesk documentation scope** - #6542 covers action toolbar, #6549 covers streaming log panel. Both need erkdesk component docs, IPC patterns, and testing guides. **Merge strategy**: Combine into unified erkdesk documentation items.

3. **#6550 (context menu) extends #6542 (toolbar)** - context menu reuses ActionDef/availability predicates from toolbar. **Merge strategy**: Document together since they share the same architecture.

### Corrections to Original Plans

- **#6554**: Claims "All Documentation Complete" but 0 docs found on master. Branch P6547 has them.
- **#6556**: `roadmap-mutation-semantics.md` is OUTDATED and misleading agents (describes pre-fix behavior)
- **#6549**: Some docs exist on branch P6549 (commit 30c37299f) but not merged to master

### Key Discovery: Unmerged Documentation PRs

Two PRs have documentation work that should be merged BEFORE creating new docs:
- **PR #6548** (from #6547): 9 new doc files + 10 updates (subagent delegation, optimization patterns)
- **PR #6549 branch**: Streaming IPC docs, erkdesk component docs, migration guides

These PRs should be reviewed and merged first to avoid duplicating work.

## Remaining Gaps (After Merging Pending PRs)

### Category A: Graphite/Git Patterns (from #6557)

Documentation items that remain unimplemented regardless of pending PRs:

1. Add "Retracking Required After Commit Amend" subsection to git-graphite-quirks.md
2. Update pr-submit-pipeline.md Step 8 to mention "retrack Graphite"
3. Update pr-submit-phases.md Phase 6 with retracking explanation
4. Add tripwire: "amending a commit when Graphite is enabled"

### Category B: Objective Roadmap (from #6556)

1. **CRITICAL**: Fix outdated `roadmap-mutation-semantics.md` (describes pre-fix behavior)
2. Create `docs/learned/objectives/roadmap-status-system.md` (consolidated two-tier reference)
3. Create `docs/learned/objectives/roadmap-mutation-patterns.md` (surgical vs full-body updates)
4. Update `docs/learned/objectives/objective-roadmap-check.md` with explicit status support

### Category C: erkdesk Documentation (from #6542, #6549, #6550)

After merging pending PRs, remaining gaps:

1. Create `docs/learned/desktop-dash/app-architecture.md` - App component state management, lifting pattern, auto-refresh, keyboard nav
2. Create `docs/learned/desktop-dash/action-toolbar.md` - Actions table, availability predicates, styling reference
3. Create `docs/learned/desktop-dash/ipc-actions.md` - IPC handler pattern, 4-location checklist
4. Create `docs/learned/desktop-dash/context-menu-system.md` - Context menu architecture, discriminated unions _(only if #6550 branch merges)_
5. Update `docs/learned/desktop-dash/tripwires.md` - Add IPC handler cleanup, type exhaustiveness, test mock completeness tripwires

### Category D: Subagent Optimization (from #6554, #6547)

**These items are ALL implemented on PR #6548 branch.** If that PR merges, no new documentation is needed for this category. If it doesn't merge, the following would need creation:

- `docs/learned/architecture/subagent-delegation-for-optimization.md`
- `docs/learned/architecture/subagent-prompt-structure.md`
- `docs/learned/architecture/subagent-self-validation.md`
- `docs/learned/architecture/task-tool-patterns.md`
- `docs/learned/optimization/turn-count-profiling.md`
- `docs/learned/reference/subagent-model-selection.md`

## Implementation Steps

### Step 1: Check and merge pending documentation PRs

**Action**: Review PRs #6548 and check if branch P6549 has an open PR with documentation.

```bash
gh pr view 6548 --json state,mergeable,statusCheckRollup
```

If PRs are ready, merge them to avoid duplicating work. If not mergeable, proceed with creating docs from scratch.

### Step 2: Fix outdated roadmap-mutation-semantics.md _(from #6556)_

**File:** `docs/learned/architecture/roadmap-mutation-semantics.md`

**Changes needed:**
- Update tripwire (line ~9) to reflect two-tier status resolution
- Update inference rules table (lines ~20-25) to include explicit status values
- Update explanation section (lines ~27-36) to describe computed status
- Update parser inference logic (lines ~42-47) to show done/in-progress/pending as explicit

**Source:** `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py` lines 102-110

**Verification:** Document matches current parser behavior

### Step 3: Create roadmap-status-system.md _(from #6556)_

**File:** `docs/learned/objectives/roadmap-status-system.md`

**Content outline:**
1. Two-tier status resolution system
2. Tier 1: Explicit status values (done, in-progress, pending, blocked, skipped)
3. Tier 2: PR-based inference (# → done, plan # → in_progress, empty → pending)
4. Priority ordering: explicit overrides inference
5. Code reference: `objective_roadmap_shared.py:102-110`

**Verification:** Document accurately describes parsing in objective_roadmap_shared.py

### Step 4: Add Graphite retrack documentation _(from #6557)_

**File:** `docs/learned/architecture/git-graphite-quirks.md`

**Changes:** Add "Retracking Required After Commit Amend" subsection after line ~352:
- Code pattern showing retrack after amend
- References to submit_pipeline.py:666-668 and sync_cmd.py:254,319
- Add tripwire to frontmatter

**File:** `docs/learned/cli/pr-submit-pipeline.md`
- Update Step 8 description (line ~37) to include "retrack Graphite"

**File:** `docs/learned/pr-operations/pr-submit-phases.md`
- Update Phase 6 description (lines ~104-115) with retracking explanation

**Verification:** Documentation matches code at submit_pipeline.py:666-668

### Step 5: Create erkdesk architecture docs _(from #6542, #6549, #6550)_

**File:** `docs/learned/desktop-dash/app-architecture.md`

**Content outline:**
1. App.tsx as state owner (plans, selectedIndex, loading, error, log state)
2. State lifting pattern: PlanList and ActionToolbar as controlled components
3. Auto-refresh every 15s with selection preservation by issue_number
4. Keyboard navigation (j/k, arrows)
5. URL loading strategy (pr_url preferred over issue_url)

**File:** `docs/learned/desktop-dash/action-toolbar.md`

**Content outline:**
1. 5 actions: Submit, Land, Address, Fix Conflicts, Close
2. Availability predicates table with exact conditions
3. Streaming execution pattern (spawn + events, not blocking)
4. ActionDef interface and ACTIONS array (exported for reuse)
5. CSS styling reference (dark theme colors)

**File:** `docs/learned/desktop-dash/ipc-actions.md`

**Content outline:**
1. IPC handler registration pattern
2. Four-location checklist: main, preload, types, test mock
3. Streaming vs blocking execution
4. Cleanup pattern: removeHandler + removeAllListeners on window close
5. ANSI stripping for subprocess output

**Source:** `erkdesk/src/main/index.ts`, `erkdesk/src/main/preload.ts`, `erkdesk/src/types/erkdesk.d.ts`

**Verification:** Each document references actual file paths and line numbers

### Step 6: Update erkdesk tripwires _(from #6542, #6549)_

**File:** `docs/learned/desktop-dash/tripwires.md`

**Add 3 tripwires:**
1. IPC Handler Cleanup (score 6/10): Must call removeHandler() and removeAllListeners() on window close
2. IPC Event Listener Cleanup (score 5/10): removeActionListeners() prevents memory leaks
3. Four-Location IPC Updates (score 4/10): main, preload, types, test mock must stay in sync

### Step 7: Create roadmap-mutation-patterns.md _(from #6556)_

**File:** `docs/learned/objectives/roadmap-mutation-patterns.md`

**Content outline:**
1. Surgical update pattern (update-roadmap-step for single cells)
2. Full-body update pattern (objective-update-with-landed-pr for complete rewrites)
3. When to use each pattern
4. LBYL defensive coding examples from status inference

### Step 8: Update index files and tripwire counts

**Files:** Update `docs/learned/index.md`, category index files, and `tripwires-index.md` to reflect new documents.

Run `erk docs sync` to regenerate auto-generated files.

## Attribution

Items by source:
- **#6557**: Steps 4 (Graphite retrack docs)
- **#6556**: Steps 2, 3, 7 (roadmap docs)
- **#6554**: Step 1 (merge pending PR - docs already on branch)
- **#6550**: Step 5 (context menu docs, conditional on merge)
- **#6549**: Steps 5, 6 (erkdesk streaming docs)
- **#6547**: Step 1 (merge pending PR - docs already on branch)
- **#6542**: Steps 5, 6 (erkdesk toolbar docs)