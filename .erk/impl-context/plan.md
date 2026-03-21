# Plan: Consolidated Documentation from 20 erk-learn Plans

> **Consolidates:** #9370, #9369, #9368, #9362, #9360, #9359, #9357, #9356, #9354, #9351, #9349, #9347, #9345, #9343, #9342, #9341, #9339, #9336, #9334, #9331

## Context

20 erk-learn plans accumulated from recent implementation sessions. All source PRs are merged — no code changes needed. This plan captures the documentation opportunities discovered during those implementations.

## Source Plans

| # | Title | Items |
| --- | --- | --- |
| #9370 | Fix stale plan-to-PR terminology in docs/learned/ | 12 stale refs |
| #9369 | Enable dangerous mode propagation in objective plan | 1 item |
| #9362 | Promote objective-reevaluate → objective-reconcile | 2 items |
| #9360 | Delete dead functions from plan_header.py | 1 item |
| #9359 | Rename plan-to-PR modules (Phase 2) | merged into #9370 |
| #9357 | Introduce PlanHeaderData frozen dataclass | 2 items |
| #9349 | Rename PlanContext → PrContext | merged into #9370 |
| #9347 | Fix multi-node landing: store node_ids | 1 item |
| #9356 | Decouple pool config from core erk config | 1 item |
| #9354 | Push PR Feedback Classification into CLI | 1 item |
| #9351 | TUI close command works with Graphite URLs | 1 item |
| #9368 | Move navigation commands to erk_slots | 2 items |
| #9339 | Add slot goto command | 1 item |
| #9334 | Move slot allocation to erk_slots | merged into #9368 |
| #9343 | Refactor teleport dry-run to action plan pattern | 1 item |
| #9341 | Add --dry-run flag to erk pr teleport | merged into #9343 |
| #9342 | Delete erk branch create command | 0 (no doc needed) |
| #9345 | Fix: source <(erk --script) output | 1 item |
| #9336 | Standardize "planned PR" terminology | merged into #9370 |
| #9331 | Allow [erk-learn] title prefix in dispatch | 1 item |

## Overlap Analysis

- **#9370, #9359, #9349, #9336** all relate to plan-to-PR terminology — consolidated into a single terminology fix step
- **#9341 + #9343** both cover teleport dry-run — consolidated into action plan pattern doc
- **#9334 + #9368** both cover erk_slots package growth — consolidated into package overview doc
- **#9342** (delete branch create) needs no documentation — command simply removed

## Implementation Steps

### Step 1: Fix stale plan-to-PR terminology in docs/learned/

_(from #9370, #9359, #9349, #9336)_

**Files to update** (mechanical find-and-replace):

| File | Line(s) | Old | New |
| --- | --- | --- | --- |
| `docs/learned/architecture/pr-body-assembly.md` | 26 | `PlanContext` | `PrContext` |
| `docs/learned/pr-operations/plan-embedding-in-pr.md` | 26 | `PlanContext` | `PrContext` |
| `docs/learned/architecture/agent-backpressure-gates.md` | 69 | `validate_plan_title` | `validate_pr_title` |
| `docs/learned/cli/exec-script-performance.md` | 9, 54, 58 | `PlanListService` | `PrListService` |
| `docs/learned/planning/learn-plan-metadata-fields.md` | 95 | `PlanListService` | `PrListService` |
| `docs/learned/tui/plan-title-rendering-pipeline.md` | 60 | `PlanListService` | `PrListService` |
| `docs/learned/architecture/gateway-vs-backend.md` | 49-60 | `plan_store/` paths | `pr_store/` paths |
| `docs/learned/architecture/erk-shared-package.md` | 32 | `plan_store/` tree entry | `pr_store/` |
| `docs/learned/architecture/erk-architecture.md` | 372, 374 | `plan_store/backend.py` | `pr_store/backend.py` |
| `docs/learned/planning/planned-pr-backend.md` | 37 | `plan_store/planned_pr.py` | `pr_store/planned_pr.py` |
| `docs/learned/planning/planned-pr-lifecycle.md` | 85 | `plan_store/` path | `pr_store/` path |
| `docs/learned/planning/branch-plan-resolution.md` | 20, 46 | `plan_store/` paths | `pr_store/` paths |

**Verification:** `grep -r "PlanContext\|PlanListService\|validate_plan_title\|plan_store/" docs/learned/` returns no matches.

### Step 2: Create action plan pattern doc

_(from #9343, #9341)_

**File:** `docs/learned/architecture/action-plan-pattern.md`

**Content outline:**
1. **Pattern**: Build a frozen dataclass describing mutations, then display or execute
2. **Motivation**: Replaces boolean parameter threading with typed plan objects
3. **Case study**: `TeleportPlan` in `src/erk/cli/commands/pr/teleport_cmd.py:38-56`
   - Fields: pr_number, branch_name, ahead, behind, staged, modified, untracked, has_slot, etc.
   - Two-phase flow: `_build_teleport_plan()` → display (dry-run) or execute
4. **When to use**: Commands with preview/dry-run capability, force-reset operations
5. **Integration**: `--dry-run` flag triggers display-only path; `--script` is incompatible with dry-run

**Verification:** Doc accurately describes `TeleportPlan` fields matching `teleport_cmd.py`.

### Step 3: Create erk_slots package overview doc

_(from #9368, #9339, #9334)_

**File:** `docs/learned/erk/erk-slots-package.md`

**Content outline:**
1. **Purpose**: Self-contained package for slot/pool management
2. **Module breakdown**: group.py, common.py, config.py, command modules (assign, checkout, goto, unassign, init_pool, list, repair), diagnostics.py, navigation.py
3. **Key functions in common.py**: `allocate_slot_for_branch()`, `find_inactive_slot()`, `find_next_available_slot()`, `sync_pool_assignments()`
4. **Navigation commands**: `erk slot up/down/goto` — moved from core CLI
5. **Navigation helper split**: Orchestration in `erk_slots/navigation.py`, shared utilities in `src/erk/cli/commands/navigation_helpers.py`
6. **Config independence**: Pool config loaded via `erk_slots.config.load_pool_config()`, not through LoadedConfig

**Verification:** Module list matches `packages/erk-slots/src/erk_slots/` directory contents.

### Step 4: Create objective reconciliation workflow doc

_(from #9362, #9369)_

**File:** `docs/learned/objectives/objective-reconciliation-workflow.md`

**Content outline:**
1. **What**: Audit objectives against codebase, identify stale references, mark completed nodes
2. **When**: Automatically runs as Step 2.5 in `/erk:objective-plan`; manual via `erk objective reconcile`
3. **6 phases**: validate → extract → verify → findings → propose → execute
4. **Finding types**: STALE, DONE, CURRENT, UNCLEAR
5. **Dangerous mode**: `-d/--dangerous` flag propagated from `plan_cmd.py:738` using None-preservation pattern
6. **Source**: `.claude/commands/erk/objective-reconcile.md` (286-line skill)

**Verification:** Skill file exists and phases match description.

### Step 5: Create typed metadata pattern doc

_(from #9357, #9360)_

**File:** `docs/learned/architecture/typed-metadata-pattern.md`

**Content outline:**
1. **Pattern**: Parse-once/access-many via frozen dataclass with `from_dict()`, `to_dict()`, `to_metadata_block()`
2. **Case study**: `PlanHeaderData` — 2 required + 32 optional fields
3. **Serialization boundary**: `tuple[str, ...]` internally ↔ `list` at JSON boundaries
4. **Helper refactoring**: `_update_plan_header()` reduces boilerplate from ~12 lines to ~3-5 lines per update function
5. **Testing**: Round-trip serialization tests, frozen semantics verification

**Verification:** `PlanHeaderData` class exists in codebase with documented fields.

### Step 6: Create multi-node plans doc

_(from #9347)_

**File:** `docs/learned/planning/multi-node-plans.md`

**Content outline:**
1. **Problem**: Multi-node PRs only marked first node as done during landing
2. **Solution**: `node_ids` field in plan-header metadata for durable storage
3. **Auto-discovery**: `objective_apply_landed_update()` uses plan metadata as primary source, falls back to PR refs
4. **Schema**: `NODE_IDS` constant with list validation in `schemas.py`
5. **Flow**: Plan creation writes node_ids → landing reads them → objective updated

**Verification:** `node_ids` field exists in PlanHeaderData and Plan dataclass.

### Step 7: Create feedback classification architecture doc

_(from #9354)_

**File:** `docs/learned/pr-operations/feedback-classification-architecture.md`

**Content outline:**
1. **Two-stage pipeline**: mechanical (CLI) → semantic (LLM skill)
2. **Stage 1** (`classify-pr-feedback` exec command): bot detection, state interpretation, restructuring analysis via `git diff -M -C`
3. **Stage 2** (pr-feedback-classifier skill): action_summary, complexity assessment, batch construction
4. **Data flow**: CLI JSON output → skill input → batched output
5. **Source**: `src/erk/cli/commands/exec/scripts/classify_pr_feedback.py` (493 lines)

**Verification:** Exec command registered in `exec/group.py`.

### Step 8: Create pool config decoupling doc

_(from #9356)_

**File:** `docs/learned/erk/pool-config-decoupling.md`

**Content outline:**
1. **What changed**: Pool config moved from `LoadedConfig` to `erk_slots.config.load_pool_config()`
2. **Pattern**: Subsystems read their own config independently
3. **Implementation**: `PoolConfig` dataclass with fallback to `DEFAULT_POOL_SIZE = 4`
4. **Removed**: `pool_size`, `pool_checkout_shell`, `pool_checkout_commands` from LoadedConfig/RepoConfigSchema
5. **Source**: `packages/erk-slots/src/erk_slots/config.py` (59 lines)

**Verification:** Pool fields absent from LoadedConfig; `load_pool_config()` exists.

### Step 9: Create TUI Graphite URL handling doc

_(from #9351)_

**File:** `docs/learned/tui/graphite-url-handling.md`

**Content outline:**
1. **Problem**: TUI close command failed with Graphite URLs (different format than GitHub)
2. **Solution**: Use `self._location.repo_id` (structured data) instead of URL parsing
3. **Removed**: `_parse_owner_repo_from_url()` helper
4. **Pattern**: Prefer repository context over URL string parsing
5. **Source**: `packages/erk-shared/src/erk_shared/gateway/pr_service/real.py:70-88`

**Verification:** No URL parsing in `close_pr()` method.

### Step 10: Create script flag behavior doc

_(from #9345)_

**File:** `docs/learned/cli/script-flag-behavior.md`

**Content outline:**
1. **What `--script` does**: Emits activation script content for shell integration
2. **Interaction with other flags**: `--script` + `--dry-run` → script disabled, dry-run takes precedence
3. **Hidden option**: Only visible with `show_hidden_commands=True`
4. **Use cases**: cmux integration, non-interactive shell setup
5. **Source**: `teleport_cmd.py:115-122`, `activation.py`

**Verification:** Script flag exists on teleport command.

### Step 11: Create erk-learn dispatch doc

_(from #9331)_

**File:** `docs/learned/planning/erk-learn-plan-dispatch.md`

**Content outline:**
1. **Title prefix**: Both `[erk-pr]` and `[erk-learn]` accepted by `has_plan_title_prefix()`
2. **Dispatch compatibility**: `dispatch_cmd.py:166-167` validates via shared prefix function
3. **Label assignment**: `erk-learn` label added during plan-save with `--plan-type=learn`
4. **Lifecycle**: Learn plans follow same dispatch/implement flow as regular plans

**Verification:** `has_plan_title_prefix()` returns True for both prefixes.

### Step 12: Update docs/learned/ index and tripwires

Update `docs/learned/index.md` to include new documents in their respective category listings. Add relevant tripwires to category tripwire files for new patterns.

## Verification

1. Run `grep -r "PlanContext\|PlanListService\|validate_plan_title\|plan_store/" docs/learned/` — expect no matches after Step 1
2. Each new doc file exists and has correct frontmatter
3. All code references in new docs point to files/functions that exist on master
4. Index entries added for all new docs

## Attribution

| Source Plans | Steps |
| --- | --- |
| #9370, #9359, #9349, #9336 | Step 1 |
| #9343, #9341 | Step 2 |
| #9368, #9339, #9334 | Step 3 |
| #9362, #9369 | Step 4 |
| #9357, #9360 | Step 5 |
| #9347 | Step 6 |
| #9354 | Step 7 |
| #9356 | Step 8 |
| #9351 | Step 9 |
| #9345 | Step 10 |
| #9331 | Step 11 |
| All | Step 12 |
| #9342 | No doc needed (command deletion) |
