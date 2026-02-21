# Plan: Consolidated Documentation for Feb 21 Implementations

> **Consolidates:** #7755, #7753, #7752, #7751, #7748, #7742, #7737, #7732, #7710, #7707, #7703, #7701

## Context

12 erk-learn plans were generated from implementation sessions on 2026-02-21. All code changes are merged. This plan consolidates them into documentation work: fixing incorrect docs, adding missing tripwires, and creating new feature docs. Plan #7751 (gist → branch transport) is deferred because its PR (#7733) hasn't merged yet.

---

## Source Plans

| #    | Title                                         | Code Status | Docs Needed    |
|------|-----------------------------------------------|-------------|----------------|
| 7703 | Fix learn pipeline for draft-PR plans         | ✅ Merged   | 2 new docs     |
| 7707 | Rename 'instruction' to 'prompt'              | ✅ Merged   | None (complete)|
| 7710 | Auto-force push for plan impl branches        | ✅ Merged   | 1 new doc      |
| 7732 | Replace "issue" with "plan" in CLI output     | ✅ Merged   | 2 doc updates  |
| 7737 | One-shot dispatch metadata for draft_pr       | ✅ Merged   | 4 tripwires    |
| 7742 | Move plan backend config to GlobalConfig      | ✅ Merged   | 3 new docs + tripwires |
| 7748 | Simplify plan backend to env vars             | ✅ Merged   | 3 tripwires    |
| 7751 | Replace gist with branch-based materials      | ❌ PR open  | DEFERRED       |
| 7701 | Add branch column to TUI dashboard            | ✅ Merged   | 1 new doc      |
| 7752 | Fix impl-context cleanup convergence          | ✅ Merged   | 1 correction + 1 new doc |
| 7753 | Add `erk wt create-from` command              | ✅ Merged   | 1 new doc      |
| 7755 | Upgrade objective-plan safety guardrails      | ✅ Merged   | 1 critical fix |

---

## Investigation Findings

### Corrections to Original Plans

- **#7748**: Plan title says "only environment variables" but `get_plan_backend()` still has three-tier resolution (env var → `GlobalConfig.plan_backend` → "github"). The PR simplified some aspects but didn't remove the GlobalConfig tier. Documentation should describe the CURRENT three-tier system.
- **#7751**: Not yet merged (PR #7733 is open); gist transport still active. Documenting the branch-based system now would create contradictions.

### Critical Factual Error

- `docs/learned/planning/token-optimization-patterns.md` says `/erk:objective-plan` uses `haiku` as a canonical example. **This is wrong.** PR #7750 upgraded it to `sonnet` with safety guardrails. This is an actively misleading error.

### Implementation Verification

- **#7710 auto-force**: Confirmed in `src/erk/cli/commands/pr/submit_pipeline.py` — `is_plan_impl = state.issue_number is not None`, `effective_force = state.force or is_plan_impl`
- **#7753 wt create-from**: Confirmed in `src/erk/cli/commands/wt/create_from_cmd.py` — fully implemented with force flag, slot cleanup, activation scripts
- **#7701 TUI branch column**: Confirmed in `src/erk/tui/widgets/plan_table.py:181`
- **#7742 GlobalConfig.plan_backend**: Confirmed in `packages/erk-shared/src/erk_shared/context/types.py:239`

---

## Implementation Steps

### Step 1: Fix Critical Factual Error (IMMEDIATE)

**File:** `docs/learned/planning/token-optimization-patterns.md`

Find the section that cites `/erk:objective-plan` as a canonical haiku example and correct it:
- Change: "haiku" → "sonnet"
- Add note: As of PR #7750, objective-plan uses sonnet for better multi-step reasoning
- Remove/update any claim that haiku is preferred for this command

**Verification:** Confirm no reference to haiku for objective-plan exists in this file.

---

### Step 2: Update impl-context.md to Reflect Convergence Fix

**File:** `docs/learned/planning/impl-context.md`

The "Why It Can Leak" section and path descriptions are outdated. PR #7747 ensured all 5 setup paths converge at a single cleanup point:
- Replace "three paths" description with "five paths that converge at Step 2d"
- Remove warnings about cleanup not running for some paths (now fixed)
- Add note: cleanup is idempotent, safe to run multiple times

**Source:** Investigation of #7752 and PR #7747.

---

### Step 3: Add Missing Tripwires to planning/tripwires.md

**File:** `docs/learned/planning/tripwires.md`

Add these tripwires (from plans #7737, #7742, #7748, #7752):

1. **Self-referential close prevention**: When a draft PR is the plan itself, it cannot close itself. The plan's "implementation complete" event cannot reference the plan PR as the implementing PR. Guard against this pattern in one-shot dispatch.

2. **One-shot metadata block preservation**: The one-shot metadata block in the plan body must survive all edits (plan creation, replan, etc.). Never strip HTML comment blocks that contain `erk:metadata-block` markers.

3. **Backend detection precedence**: Context-based backend detection (`GlobalConfig.plan_backend` passed via context) takes precedence when available. Never fall back to re-reading env vars inside inner functions if `global_config` is already in scope.

4. **Draft-PR backend propagation**: When spawning GitHub Actions workflows from erk, pass `plan_backend: draft_pr` explicitly as a workflow input. GitHub Actions reusable workflows do NOT inherit the caller's environment variables — the env var must be explicitly forwarded as an input.

5. **Impl-context cleanup routing**: All code paths that set up an implementation context must route through the single convergence point that runs cleanup. Adding a new setup path without routing through the convergence point will silently skip cleanup.

---

### Step 4: Add Missing Tripwires to testing/tripwires.md

**File:** `docs/learned/testing/tripwires.md`

Add these tripwires (from plans #7737, #7742, #7732):

1. **CliRunner env var isolation**: When testing code that reads `ERK_PLAN_BACKEND` or other environment variables, use `CliRunner(env={"ERK_PLAN_BACKEND": "..."})` to isolate the test. Ambient env vars from the developer shell leak into CliRunner by default and cause intermittent test failures.

2. **Test assertion lag**: When production code changes a user-facing string (e.g., "issue" → "plan"), test assertions using the old string will silently pass against stale snapshots. Always grep tests for old string literals after renaming display strings.

---

### Step 5: Add Missing Tripwires to ci/tripwires.md

**File:** `docs/learned/ci/tripwires.md`

Add (from plan #7748):

1. **Reusable workflow input forwarding**: GitHub Actions reusable workflows (via `workflow_call`) do NOT inherit environment variables from the caller workflow. Any env var that affects behavior (like `ERK_PLAN_BACKEND`) must be declared as an explicit `input` in the reusable workflow and passed by the caller.

---

### Step 6: Add Missing Tripwire to architecture/tripwires.md

**File:** `docs/learned/architecture/tripwires.md`

Add (from plan #7742):

1. **PlanBackendType canonical import**: Import `PlanBackendType` only from `erk_shared.context.types`. Do not re-declare or shadow this type in other modules.

---

### Step 7: Create plan-implementation-auto-force.md

**File:** `docs/learned/pr-operations/plan-implementation-auto-force.md`

Content:
- **What it does**: `erk pr submit` auto-applies force-push when the current branch is a plan implementation branch (detected via `state.issue_number is not None`, which is set when `.impl/` is valid)
- **Why it's safe**: Plan implementation branches always diverge from remote because `erk implement` creates them fresh and `.impl/` gets committed locally. Force-push is expected and harmless.
- **Code location**: `src/erk/cli/commands/pr/submit_pipeline.py` — `is_plan_impl = state.issue_number is not None`, `effective_force = state.force or is_plan_impl`
- **User experience**: CLI prints `"   Auto-forcing: plan implementation branch"` when auto-force triggers
- **When it doesn't apply**: Regular feature branches (no `.impl/` folder) are not auto-forced

---

### Step 8: Create draft-pr-learn-pipeline.md

**File:** `docs/learned/planning/draft-pr-learn-pipeline.md`

Content:
- **The problem**: Draft-PR plans use the PR number as their plan ID. The original learn pipeline discovered plan IDs via branch name → metadata lookup, which only worked for GitHub Issue-based plans.
- **The fix**: When `plan_backend == "github-draft-pr"`, use the PR number directly as the plan ID (short-circuit the branch-name discovery step). Implemented in `trigger_async_learn.py`.
- **Metadata fallback**: For draft-PR plans, the gist URL (learn materials location) is stored as a comment on the PR (not in a metadata block), requiring a comment-based fallback in `land_cmd.py`.
- **Affected files**: `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`, `src/erk/cli/commands/pr/land_cmd.py`, `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py`

---

### Step 9: Create wt-create-from.md

**File:** `docs/learned/cli/wt-create-from.md` (or `docs/learned/erk/wt-create-from.md`)

Content:
- **Purpose**: `erk wt create-from <branch>` allocates a worktree slot to an already-existing branch (vs `erk wt create` which creates a new branch)
- **When to use**: When you have an existing branch (e.g., from a remote PR) and want to set up a local worktree for it
- **Decision tree**: `wt create` (new branch, new worktree) vs `wt create-from` (existing branch, new worktree) vs `wt checkout` (if that exists)
- **Implementation details**: Validates branch existence, auto-fetches tracking branches, supports `--force` to reuse an occupied slot (runs artifact cleanup first), generates activation scripts
- **Code location**: `src/erk/cli/commands/wt/create_from_cmd.py`

---

### Step 10: Create tui/dashboard-columns.md

**File:** `docs/learned/tui/dashboard-columns.md`

Content:
- **Column inventory**: List all columns in the plan table with their purpose (plan #, title, status, objective, branch, etc.)
- **Backend-conditional columns**: Some columns only appear in draft_pr mode (e.g., branch column at `plan_table.py:181`)
- **Column ordering principles**: Why columns are ordered the way they are
- **Code location**: `src/erk/tui/widgets/plan_table.py`

---

### Step 11: Update docs/learned/cli/output-styling.md

**File:** `docs/learned/cli/output-styling.md`

Add a "User-Facing Terminology Guidelines" section with:
- Table: When to use "plan" vs "issue" vs "PR" in user-facing output
- Rule: Use "plan" for all user-facing references to plan items (backend-agnostic)
- Rule: Use "PR" when specifically referring to pull requests
- Rule: Internal variable names (`issue_number`) may differ from display strings
- Reference: This was standardized in PR #7732

---

### Step 12: Defer gist → branch transport docs (Plan #7751)

**Do not create documentation for the branch-based learn transport until PR #7733 merges.**

When PR #7733 merges, a follow-up plan should:
- Archive `docs/learned/architecture/gist-materials-interchange.md` (entire document becomes stale)
- Rewrite `docs/learned/planning/learn-pipeline-workflow.md` Stage 4 (gist upload → branch push)
- Update `docs/learned/planning/async-learn-local-preprocessing.md` Material Assembly section
- Update `docs/learned/planning/tripwires.md` to remove stale gist format tripwire
- Create `docs/learned/architecture/learn-branch-transport.md`
- Update 5+ other docs that reference gist transport

---

## Files to Modify

### Critical (Step 1-2):
- `docs/learned/planning/token-optimization-patterns.md` — fix haiku→sonnet error
- `docs/learned/planning/impl-context.md` — update convergence description

### Tripwires (Steps 3-6):
- `docs/learned/planning/tripwires.md` — add 5 tripwires
- `docs/learned/testing/tripwires.md` — add 2 tripwires
- `docs/learned/ci/tripwires.md` — add 1 tripwire
- `docs/learned/architecture/tripwires.md` — add 1 tripwire

### New Files (Steps 7-10):
- `docs/learned/pr-operations/plan-implementation-auto-force.md` (new)
- `docs/learned/planning/draft-pr-learn-pipeline.md` (new)
- `docs/learned/cli/wt-create-from.md` (new)
- `docs/learned/tui/dashboard-columns.md` (new)

### Updates (Step 11):
- `docs/learned/cli/output-styling.md` — add terminology table

---

## Overlap Analysis

- Plans #7737, #7742, #7748 all relate to plan backend configuration → consolidated into tripwire additions + configuration docs
- Plans #7703 and #7732 both involve backend-agnostic terminology → covered in output-styling.md update + draft-pr-learn-pipeline.md
- Plans #7701, #7752, #7753, #7755 are independent feature areas → separate docs

---

## Verification

After implementation, verify:
1. `grep -r "haiku" docs/learned/planning/token-optimization-patterns.md` — should not find objective-plan haiku reference
2. `grep -r "three paths" docs/learned/planning/impl-context.md` — should return no results (or only in historical context)
3. Each new file exists and accurately describes the feature by cross-referencing the source files listed above
4. Run `erk docs sync` to regenerate the tripwires index after updating tripwires files
