# Documentation Plan: Delete get_plan_backend() and PlanBackendType (objective #7911 node 1.1)

## Context

PR #7971 completed node 1.1 of objective #7911, which eliminates the dual-backend plan storage system by deleting `get_plan_backend()` and `PlanBackendType`. The change touched 24 files (+28/-958 lines), mechanically replacing every call to `get_plan_backend()` with the hardcoded literal `"draft_pr"` and removing the `PlanBackendType` alias. This is the first of three nodes: node 1.1 deletes the selector, node 1.2 removes dead branches, and node 1.3 removes the now-redundant `plan_backend` parameters from TUI code.

Five existing docs now contain phantom references to deleted symbols (`get_plan_backend()`, `PlanBackendType`, `ERK_PLAN_BACKEND` as a live config). These phantom references actively mislead agents: an agent reading `erk-shared-package.md` would try to import a type that no longer exists, and an agent reading `draft-pr-plan-backend.md` would believe backend selection is dynamic when it is now hardcoded. Cleaning these stale references is the highest priority.

The session also surfaced two non-obvious operational insights: `erk exec plan-save --format json` routes duplicate-detection output to stderr (not stdout), causing silent-success confusion; and the `roadmap-step` marker must exist before `plan-save` runs or the objective roadmap silently fails to update. Both warrant tripwires.

## Raw Materials

PR #7971

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 11    |
| Contradictions to resolve      | 5     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score 2-3)| 2     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action. These must be resolved before creating new content.

### 1. Delete PlanBackendType tripwire from erk-shared-package.md

**Location:** `docs/learned/architecture/erk-shared-package.md`
**Action:** DELETE_STALE_ENTRY
**Phantom References:** `PlanBackendType` in `erk_shared.context.types` (MISSING -- type deleted in PR #7971)
**Source:** [PR #7971]

**Cleanup Instructions:**

Remove the tripwire entry from frontmatter that warns about importing `PlanBackendType` from `erk_shared.context.types`. The type no longer exists in that module. The tripwire currently reads:

> "PlanBackendType canonical import: import PlanBackendType only from erk_shared.context.types..."

This actively misleads agents into attempting to import a non-existent type. Delete the entire tripwire entry. The rest of the document (package structure, import rules) remains valid.

## Contradiction Resolutions

### 1. draft-pr-plan-backend.md -- Backend Selection section references deleted function

**Existing doc:** `docs/learned/planning/draft-pr-plan-backend.md`
**Conflict:** Doc states "Backend selection is controlled by the `ERK_PLAN_BACKEND` environment variable, read by `get_plan_backend()` in `plan_store/__init__.py:19-24`" with two options (`"github"` and `"draft_pr"`). The function is deleted; backend is now hardcoded to `"draft_pr"`.
**Resolution:** Rewrite the Backend Selection section. Remove the claim that `ERK_PLAN_BACKEND` controls backend selection. Replace with: backend is hardcoded to `"draft_pr"` in `context.py` via `PLAN_BACKEND_SPLIT` comment blocks. The `"github"` option no longer exists. Also remove the phantom `close_review_pr()` reference in `land_pipeline.py:469-471`. Multiple tripwires in the frontmatter reference the dual-backend model -- update or remove those that reference `get_plan_backend()` or assume two active backends (see items in HIGH priority below).

### 2. environment-variable-isolation.md -- Code snippet references deleted function call

**Existing doc:** `docs/learned/testing/environment-variable-isolation.md`
**Conflict:** Code snippet shows `elif get_plan_backend() == "draft_pr"` but the actual code is now `elif "draft_pr" == "draft_pr"` (a tautology). The `ERK_PLAN_BACKEND` env var is no longer read by application code.
**Resolution:** Update Root Cause section and code snippet to reflect the tautological comparison now in `testing.py`. Re-evaluate whether the monkeypatch advice is still relevant -- since the backend is always `"draft_pr"`, test isolation for the env var may be moot. Mark the env var as obsolete pending full removal.

### 3. plan-creation-pathways.md -- References get_plan_backend() in Backend Routing

**Existing doc:** `docs/learned/planning/plan-creation-pathways.md`
**Conflict:** States "The `get_plan_backend()` function...reads this variable." Function is deleted.
**Resolution:** Remove the `get_plan_backend()` reference from the Backend Routing section. Update to describe current state: backend selection is not dynamic; `"draft_pr"` is hardcoded in `context.py`.

### 4. erk-shared-package.md -- Tripwire points to deleted type

**Existing doc:** `docs/learned/architecture/erk-shared-package.md`
**Conflict:** Tripwire warns about importing `PlanBackendType` from `erk_shared.context.types`. The type no longer exists.
**Resolution:** Delete the tripwire entry entirely (covered in Stale Documentation Cleanup above).

### 5. backend-aware-commands.md -- plan_backend field type is wrong

**Existing doc:** `docs/learned/tui/backend-aware-commands.md`
**Conflict:** States "`plan_backend` field is a `PlanBackendType` value (`\"github\"` or `\"github-draft-pr\"`)" but the field is now `Literal["draft_pr"]` and `PlanBackendType` is deleted.
**Resolution:** Update the `CommandContext` description to reflect that `plan_backend` is now `Literal["draft_pr"]`. The `"github"` option is no longer valid. Flag that `_is_github_backend()` in `registry.py:33` checks `ctx.plan_backend == "github"` -- this appears to be dead code that will be cleaned up in node 1.3.

## Documentation Items

### HIGH Priority

#### 1. Update draft-pr-plan-backend.md -- remove get_plan_backend() references and stale tripwires

**Location:** `docs/learned/planning/draft-pr-plan-backend.md`
**Action:** UPDATE
**Source:** [PR #7971]

**Draft Content:**

```markdown
## Backend Selection (section rewrite)

<!-- Source: src/erk/core/context.py, create_context -->

The plan backend is hardcoded to `"draft_pr"`. All plans are stored as GitHub draft pull requests via DraftPRPlanBackend. The former `get_plan_backend()` function and `PlanBackendType` type alias were deleted in PR #7971 (objective #7911 node 1.1).

The `ERK_PLAN_BACKEND` environment variable is no longer read by application code. Setting it has no effect. CI workflows and test fixtures that reference it are vestigial and will be removed in later nodes of objective #7911.

**Note:** Some code still contains `PLAN_BACKEND_SPLIT` comment blocks marking dead branches (e.g., `if "draft_pr" != "draft_pr":` in plan_save.py). These are intentionally preserved for node 1.2 cleanup.
```

Additionally, update frontmatter tripwires:
- Remove or rewrite the tripwire "adding plan storage behavior without checking plan backend type" -- there is now only one backend
- Remove the tripwire "reading ERK_PLAN_BACKEND env var inside inner functions" -- the env var is no longer read
- Evaluate remaining tripwires about dual-backend parity -- if they assume two active backends, they are stale

#### 2. Update environment-variable-isolation.md -- fix code snippet and mark ERK_PLAN_BACKEND obsolete

**Location:** `docs/learned/testing/environment-variable-isolation.md`
**Action:** UPDATE
**Source:** [PR #7971]

**Draft Content:**

```markdown
## Root Cause (section update)

<!-- Source: packages/erk-shared/src/erk_shared/context/testing.py, context_for_test -->

After PR #7971, the `get_plan_backend()` function no longer exists. The plan backend selection in `context_for_test()` is now a tautological comparison `elif "draft_pr" == "draft_pr"` -- the draft-PR path is always taken. The `ERK_PLAN_BACKEND` environment variable is no longer read by application code.

Tests that set `ERK_PLAN_BACKEND` are now exercising dead code paths. Monkeypatching this variable has no behavioral effect. These test fixtures will be cleaned up in later nodes of objective #7911.
```

#### 3. Update plan-creation-pathways.md -- remove get_plan_backend() reference

**Location:** `docs/learned/planning/plan-creation-pathways.md`
**Action:** UPDATE
**Source:** [PR #7971]

**Draft Content:**

```markdown
## Backend Routing (section update)

The plan backend is hardcoded to `"draft_pr"`. All plan creation routes through DraftPRPlanBackend. The former dynamic backend selection via `get_plan_backend()` was removed in PR #7971 (objective #7911 node 1.1). There is no longer a `"github"` issue-based plan storage path.
```

#### 4. Update backend-aware-commands.md -- fix plan_backend type and flag dead code

**Location:** `docs/learned/tui/backend-aware-commands.md`
**Action:** UPDATE
**Source:** [PR #7971]

**Draft Content:**

```markdown
## CommandContext (section update)

The `plan_backend` field on CommandContext is typed as `Literal["draft_pr"]` after PR #7971. The former `PlanBackendType` type alias (which included `"github"`) was deleted. The only valid value is `"draft_pr"`.

**Transitional state:** The `plan_backend` parameter still exists on several TUI entry points (`app.py`, `plan_table.py`, `types.py`) but is redundant -- it always carries `"draft_pr"`. These parameters are scheduled for removal in objective #7911 node 1.3. Do not add new callers or expand usage of `plan_backend` in TUI code.

**Dead code note:** `_is_github_backend()` in `src/erk/tui/commands/registry.py` checks `ctx.plan_backend == "github"`, which can never be true. This will be removed in node 1.3.
```

#### 5. Update draft-pr-plan-backend.md -- mark ERK_PLAN_BACKEND as obsolete

**Location:** `docs/learned/planning/draft-pr-plan-backend.md`
**Action:** UPDATE (combined with item 1 above)
**Source:** [PR #7971]

This is combined with item 1. When rewriting the Backend Selection section, explicitly state that `ERK_PLAN_BACKEND` is obsolete. Any mention of the env var controlling behavior should be changed to past tense, with a note that it will be fully removed in later nodes of #7911.

### MEDIUM Priority

#### 6. Document two-step backend-elimination decomposition pattern

**Location:** `docs/learned/planning/refactoring-decomposition.md` (new file)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Refactoring Decomposition for Backend Elimination
read_when:
  - "deleting a function or type that has many callers across the codebase"
  - "planning a multi-node objective that removes a backend or feature flag"
  - "decomposing a large refactor into reviewable PRs"
---

# Refactoring Decomposition for Backend Elimination

When deleting a backend selector function (or feature flag reader) that has many callers spread across the codebase, decompose the work into sequential nodes:

## The Three-Node Pattern

1. **Node N: Delete definition + mechanical replacement** -- Delete the selector function and its type alias. Replace every callsite with the hardcoded return value (e.g., `"draft_pr"`). This produces tautological comparisons (`"draft_pr" == "draft_pr"`) and always-false branches (`"draft_pr" != "draft_pr"`) that are intentionally preserved. Mark dead branches with a comment tag (e.g., `PLAN_BACKEND_SPLIT`) for the next node to find.

2. **Node N+1: Remove dead branches** -- Grep for the comment tag and remove all always-true/always-false conditional blocks. This is logic simplification, not mechanical replacement.

3. **Node N+2: Remove parameters** -- Delete function parameters, class fields, and CLI options that carried the backend type through the call chain. These are now redundant since only one value is possible.

## Why This Split Matters

- Each PR is reviewable: node N is purely mechanical (no behavioral change), node N+1 is logic simplification, node N+2 is signature cleanup
- Scope creep is prevented: the temptation to "also clean up this dead branch while I'm here" is deferred to the correct node
- Rollback is granular: each node can be reverted independently

## Reference Implementation

Objective #7911 nodes 1.1-1.3 used this pattern to eliminate the `get_plan_backend()` / `PlanBackendType` dual-backend system. Node 1.1 (PR #7971) deleted definitions and replaced 24 files. Node 1.2 removes dead branches. Node 1.3 removes `plan_backend` parameters from TUI.
```

#### 7. Document plan-save stderr routing for duplicate case

**Location:** `docs/learned/planning/draft-pr-plan-backend.md` (append section) or a dedicated plan-save doc
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## plan-save Duplicate Detection Output Routing

When `erk exec plan-save --format json` detects that a plan was already saved in the current session (via the `plan-saved-issue` marker), it returns `{"skipped_duplicate": true, "plan_number": <N>}`. This JSON is written to **stderr**, not stdout.

Empty stdout from `plan-save` does not indicate failure. Always capture both streams:

```bash
erk exec plan-save --format json --session-id "..." 2>&1
```

If stdout is empty, check stderr for the duplicate-detection response before assuming the command failed.
```

#### 8. Document TUI plan_backend intermediate state

**Location:** `docs/learned/tui/backend-aware-commands.md` (combined with item 4 above)
**Action:** UPDATE (combined with item 4)
**Source:** [PR #7971]

This is addressed as part of item 4's "Transitional state" paragraph. The key message: `plan_backend` parameters in `app.py`, `plan_table.py`, and `types.py` are typed `Literal["draft_pr"]` -- they exist but are redundant and scheduled for removal in node 1.3. Do not add new callers.

#### 9. Update dual-backend-testing.md -- verify fixture references and backend guidance

**Location:** `docs/learned/testing/dual-backend-testing.md`
**Action:** UPDATE
**Source:** [PR #7971]

**Draft Content:**

The doc currently describes a dual-backend testing model with `create_plan_store(backend=...)` dispatching to either `"github"` or `"draft_pr"`. After node 1.1:

- The `_force_github_plan_backend` fixture (from `tests/commands/dash/conftest.py`) was deleted in PR #7971. If referenced, remove it.
- The `env_overrides` section referencing `ERK_PLAN_BACKEND` is stale -- the env var no longer controls behavior.
- The "Convention" section advising parametrization across both backends needs revision: there is now only one active backend. Tests should use `"draft_pr"` only.
- The `Backend-Conditional Assertion Patterns` code block showing `@pytest.mark.parametrize("backend", ["github", "draft_pr"])` is now misleading -- the `"github"` path is dead.

```markdown
## Convention (section update)

After PR #7971 (objective #7911 node 1.1), only the `"draft_pr"` backend exists. The `"github"` issue-based backend path is dead code pending removal. New plan-related tests should use `create_plan_store(backend="draft_pr")` directly rather than parametrizing across backends.

The `ERK_PLAN_BACKEND` environment variable no longer affects behavior. `env_overrides` for this variable are inert.
```

#### 10. Mark ERK_PLAN_BACKEND as obsolete in environment-variable-isolation.md

**Location:** `docs/learned/testing/environment-variable-isolation.md`
**Action:** UPDATE (combined with item 2 above)
**Source:** [PR #7971]

This is addressed as part of item 2. The key addition: state explicitly that `ERK_PLAN_BACKEND` is obsolete and setting it has no behavioral effect after PR #7971.

### LOW Priority

#### 11. Full review of dual-backend-testing.md for stale dual-backend content

**Location:** `docs/learned/testing/dual-backend-testing.md`
**Action:** UPDATE
**Source:** [PR #7971]

**Draft Content:**

Beyond the specific updates in item 9, the entire document should be reviewed for sections that only applied to the dual-backend model:
- `create_plan_store()` dispatcher still exists but the `"github"` branch is dead code
- Backend-conditional assertion patterns with `if backend == "github":` are dead
- The frontmatter tripwire "writing plan storage tests without considering both backends" is stale -- there is only one backend now

This is LOW priority because the doc is internally consistent (it accurately describes what the code *used to* do) and the more urgent phantom references are handled in items 2, 4, and 9. A full rewrite should happen after node 1.2 when the dead `"github"` code paths are actually removed from the codebase.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. plan-save empty stdout on duplicate detection

**What happened:** `erk exec plan-save --format json` returned empty stdout when the plan had already been saved in the session. The agent initially believed the command failed silently.
**Root cause:** The duplicate-detection JSON response (`{"skipped_duplicate": true, "plan_number": N}`) is written to stderr, not stdout. Bash tool captures stdout by default.
**Prevention:** Always run `erk exec plan-save --format json ... 2>&1` to capture both streams. Check for empty stdout and examine stderr before assuming failure.
**Recommendation:** TRIPWIRE -- this is non-obvious, causes silent failure perception, and was encountered independently in both session parts.

### 2. Objective roadmap not updated after plan-save

**What happened:** The `update-objective-node` call within `plan-save` depends on the `roadmap-step` marker existing. If the marker is not created before entering plan mode, the objective roadmap table silently fails to update.
**Root cause:** The dependency between `roadmap-step` marker creation (step 5 of `objective-plan`) and `plan-save`'s ability to call `update-objective-node` is not visible from either command's interface.
**Prevention:** In the `objective-plan` workflow, always create the `roadmap-step` marker immediately after the user selects a node, before gathering context or entering plan mode.
**Recommendation:** TRIPWIRE -- invisible dependency with destructive potential (stale "pending" status leads to duplicate work).

### 3. Tests setting ERK_PLAN_BACKEND=github become silently wrong

**What happened:** After node 1.1 lands, tests that set `ERK_PLAN_BACKEND=github` no longer exercise the github backend path because `get_plan_backend()` was replaced with a hardcoded literal. The env var is ignored.
**Root cause:** Mechanical replacement of `get_plan_backend()` with `"draft_pr"` means the env var read is gone, but test fixtures that set it remain.
**Prevention:** In node 1.1 PR description, explicitly list test files that set `ERK_PLAN_BACKEND` and note they exercise dead paths. Track for cleanup in node 1.2.
**Recommendation:** ADD_TO_DOC -- specific to this objective's cleanup arc, not a broadly recurring pattern.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. plan-save empty stdout / stderr routing for duplicate detection

**Score:** 5/10 (criteria: Non-obvious +2, Silent failure +2, Repeated pattern +1)
**Trigger:** Before checking `erk exec plan-save --format json` output for empty result
**Warning:** "Empty stdout does not mean failure. The duplicate-detection path writes JSON to stderr. Always capture both streams with `2>&1` or check for empty stdout and retry with stderr capture."
**Target doc:** `docs/learned/planning/draft-pr-plan-backend.md` or a dedicated plan-save workflow doc

This is tripwire-worthy because the failure mode is completely silent -- the command exits 0, stdout is empty, and the agent proceeds believing nothing happened. The pattern was independently encountered in both parts of the session analysis, confirming it is not a one-off. Without this tripwire, every agent that runs `plan-save` with JSON format will hit the same confusion when a duplicate is detected.

### 2. Objective roadmap not updated because roadmap-step marker was skipped

**Score:** 5/10 (criteria: Non-obvious +2, Destructive potential +2, External tool quirk +1)
**Trigger:** Before calling `update-objective-node` or `plan-save` inside `objective-plan` workflow
**Warning:** "`roadmap-step` marker must be created before entering plan mode. If this marker is missing, `plan-save` cannot call `update-objective-node`, and the objective roadmap table will not update. Create the marker immediately after the user selects a node (step 5 of objective-plan), before gathering code context."
**Target doc:** `docs/learned/planning/` (objective-plan workflow doc)

This is tripwire-worthy because the consequence is invisible at execution time -- the objective roadmap shows stale "pending" status, and a subsequent agent may re-implement the same node. The dependency between the marker and the update command is not discoverable from either command's interface or help text.

## Potential Tripwires

Items with score 2-3 that may warrant promotion with additional context:

### 1. exit-plan-mode-hook overrides ExitPlanMode

**Score:** 3/10 (criteria: Non-obvious +2, Cross-cutting +1)
**Notes:** The hook intercepts `ExitPlanMode` and injects a `PLAN SAVE PROMPT` into the tool result. Claude must follow the injected instructions rather than treating the tool call as complete. This didn't meet the full threshold because it only affects Claude Code sessions (not Codex), and the hook's injection is visible in the tool result. However, if agents repeatedly call `ExitPlanMode` after the hook fires, this could be promoted to a full tripwire.

### 2. ERK_PLAN_BACKEND callers becoming dead code after node 1.1

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** After node 1.1 lands, `ERK_PLAN_BACKEND` is set in CI workflows (learn.yml, plan-implement.yml) and test files, but these settings are dead code. This is specific to objective #7911's cleanup arc and less cross-cutting than a generic tripwire. If a similar pattern recurs with other env vars being made inert by function deletion, this could be generalized into a broader tripwire about "env var reads removed but setters remain."
