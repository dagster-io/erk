# Documentation Plan: Simplify plan backend configuration to use only environment variables

## Context

This implementation session addressed a critical bug where one-shot dispatches for draft-PR plans created empty PRs. The root cause was subtle: when `one-shot.yml` calls `plan-implement.yml` as a reusable workflow, omitting the `plan_backend` input caused the value to become empty (not the default "github"), which triggered the wrong code path. Draft-PR plans were implemented on issue-based branches, resulting in empty PRs because the wrong branch was used.

The fix was minimal (3 lines across 2 files) but revealed important patterns about GitHub Actions reusable workflow behavior that's easy to get wrong. Specifically, input defaults in the called workflow do NOT apply when the input is omitted from the caller's `with:` block - the value becomes empty/null instead. This is a cross-cutting gotcha that affects all reusable workflow calls, not just this specific case.

A secondary bug was discovered during PR review: the `.erk/impl-context/` cleanup step only ran on one of five code paths through the `plan-implement.md` command, causing leaked directories in PRs. The session identified a refactoring pattern - moving operations to convergence points where all paths merge - that prevents this class of bug.

## Raw Materials

https://gist.github.com/schrockn/7ec042bf3db0b37e203e34c4576083c0

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score 2-3)| 2     |

## Documentation Items

### HIGH Priority

#### 1. Reusable Workflow Input Forwarding Tripwire

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Reusable Workflow Input Forwarding

**When:** Calling reusable workflows in GitHub Actions

**Warning:** All critical inputs must be explicitly forwarded in the `with:` block. Do not rely on defaults in the called workflow - if an input is omitted from the caller's `with:` block, the value becomes empty/null instead of using the called workflow's default. This causes silent misconfigurations where wrong code paths execute.

**Pattern:** When a reusable workflow declares `workflow_call.inputs.foo.default: "bar"`, that default only applies if the caller passes `with: { foo: something }` and the something evaluates to empty. If the caller omits `foo` entirely from the `with:` block, the value is empty, not "bar".

**Example:** See `.github/workflows/one-shot.yml` - must explicitly pass `plan_backend: ${{ inputs.plan_backend }}` to `plan-implement.yml`.

**Related:** Draft-PR backend misconfiguration tripwire in planning/tripwires.md
```

---

#### 2. Draft-PR Backend Misconfiguration Tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7740]

**Draft Content:**

```markdown
## Draft-PR Backend Propagation

**When:** Modifying one-shot dispatch or plan-implement workflow inputs

**Warning:** The `plan_backend` input must flow through the entire workflow chain (CLI -> workflow_dispatch -> reusable workflow -> environment variable). Missing propagation causes draft-PR plans to be implemented on issue-based branches, resulting in empty PRs because the wrong branch is used during implementation.

**Verification checklist:**
- CLI dispatch includes `plan_backend` in inputs dict (see `one_shot_dispatch.py`)
- Workflow declares `plan_backend` input (see `.github/workflows/one-shot.yml`)
- Workflow forwards `plan_backend` to implement job with `${{ inputs.plan_backend }}`
- Environment variable `ERK_PLAN_BACKEND` is set in implement job
- Tests assert `inputs["plan_backend"]` for both github and draft_pr backends

**Related:** Reusable workflow input forwarding tripwire in ci/tripwires.md
```

---

#### 3. Impl-Context Cleanup Path Bug Tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Multi-Path Cleanup Operations

**When:** Implementing draft-PR plans or modifying plan-implement command paths

**Warning:** Cleanup operations must execute unconditionally for all paths. In multi-path commands, place cleanup at convergence points where all paths merge, not in conditional branches. Ensure cleanup is idempotent (safe to run multiple times).

**Pattern:**
1. Identify operation that must run for all paths (e.g., `.erk/impl-context/` removal)
2. Make operation idempotent: `if [ -d path/ ]; then rm -rf path/; fi`
3. Find convergence point where all conditional paths merge
4. Place cleanup at convergence point, not in individual path branches

**Example:** See `.claude/commands/erk/plan-implement.md` - cleanup was moved from Path E only to before Step 3 where all paths (A/B/C/D/E) converge.

**Related:** Path convergence refactoring pattern (docs/learned/commands/multi-path-command-refactoring.md)
```

---

#### 4. Update draft-pr-plan-backend.md

**Location:** `docs/learned/planning/draft-pr-plan-backend.md`
**Action:** UPDATE
**Source:** [PR #7740]

**Draft Content:**

```markdown
<!-- Update existing content in the Backend Resolution section (around lines 20-22) -->

## Backend Resolution

After PR #7740, backend selection uses a simplified two-tier resolution:

1. **Environment variable** (`ERK_PLAN_BACKEND`): If set, use this value ("github" or "draft_pr")
2. **Default**: If not set, default to "github"

The previous three-tier resolution that included `global_config.plan_backend` has been removed. Backend selection is now determined entirely by the environment variable, which is set by the workflow dispatch chain.

See `packages/erk-shared/src/erk_shared/plan_store/__init__.py` for the `get_plan_backend()` implementation.
```

---

#### 5. Update config-layers.md

**Location:** `docs/learned/configuration/config-layers.md`
**Action:** UPDATE
**Source:** [PR #7740]

**Draft Content:**

```markdown
<!-- Update the GlobalConfig contents enumeration (around line 37) to remove plan_backend -->

## GlobalConfig Contents

The global configuration file contains:
- `default_branch`: The repository's default branch name
- `repo_root`: Absolute path to the repository root
<!-- NOTE: Remove plan_backend from this list - field was removed in PR #7740 -->

Backend selection for plans is now controlled exclusively via the `ERK_PLAN_BACKEND` environment variable, not persisted configuration.

See `packages/erk-shared/src/erk_shared/config/schema.py` for the current GlobalConfig schema.
```

---

### MEDIUM Priority

#### 6. Path Convergence Refactoring Pattern

**Location:** `docs/learned/commands/multi-path-command-refactoring.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Path Convergence Refactoring Pattern
category: commands
read-when: refactoring multi-path commands, adding cleanup or validation steps, fixing missed path bugs
---

# Path Convergence Refactoring Pattern

## Problem

Commands with multiple conditional paths (e.g., A/B/C/D/E based on different input states) can have operations that should run unconditionally but are mistakenly placed in only one branch.

## Solution

1. **Map all paths**: Document every conditional branch through the command
2. **Identify required operations**: Operations that must run regardless of which path was taken
3. **Find convergence points**: Points in the flow where all paths merge
4. **Ensure idempotency**: Make the operation safe to call multiple times
5. **Place at convergence**: Insert operation after convergence, not in branches

## Pattern

Operations that must run unconditionally should be:
- Idempotent (safe to run multiple times)
- Placed at convergence points (after all conditional paths merge)
- Not duplicated across branches (violates DRY, risks drift)

## Example

The `plan-implement.md` command has 5 paths:
- Path 1a: Existing `.impl/` folder
- Path 1a-file: File path input
- Path 1b-with-tracking: Issue with tracking setup
- Path 1b-without: Issue without tracking
- Path 1c: Fresh plan save

The `.erk/impl-context/` cleanup was only in Path 1c. Fixed by moving cleanup to before Step 3, where all paths converge.

See `.claude/commands/erk/plan-implement.md` for the actual implementation.

## When to Apply

- Adding a new "must always run" step to an existing command
- Debugging why a step doesn't execute on certain paths
- Refactoring command flows for clarity

## Related

- Impl-context cleanup tripwire in planning/tripwires.md
- Idempotent operations pattern (architecture/)
```

---

#### 7. Test Coverage for Workflow Inputs Tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7740]

**Draft Content:**

```markdown
## Workflow Dispatch Input Testing

**When:** Adding new workflow inputs to one-shot dispatch or similar commands

**Warning:** Tests must assert the input appears in the workflow dispatch payload with the correct value for all backend scenarios. Don't just verify function execution - verify the complete payload structure. Automated test coverage review will flag missing assertions.

**Pattern:** When adding a new input (e.g., `plan_backend`), add assertions in:
- Issue-based test: `assert inputs["plan_backend"] == "github"`
- Draft-PR test: `assert inputs["plan_backend"] == "draft_pr"`

**Example:** See `tests/commands/one_shot/test_one_shot_dispatch.py` - both `test_dispatch_happy_path()` and `test_dispatch_draft_pr_lifecycle()` assert the `plan_backend` value.

**Related:** Backend-specific testing pattern (testing/dual-backend-testing.md)
```

---

#### 8. Update one-shot-workflow.md Input Reference

**Location:** `docs/learned/workflows/one-shot-workflow.md` or `docs/learned/planning/one-shot-workflow.md`
**Action:** UPDATE
**Source:** [PR #7740]

**Draft Content:**

```markdown
<!-- Add to workflow input reference table -->

## Workflow Inputs

| Input Name | Type | Required | Default | Purpose |
|-----------|------|----------|---------|---------|
| ... | ... | ... | ... | ... |
| `plan_backend` | string | false | "github" | Specifies plan storage backend (github or draft_pr). Added in PR #7740. Forwarded to plan-implement.yml. |

The `plan_backend` input is computed by the CLI dispatch based on whether the plan is draft-PR-based. See `src/erk/cli/commands/one_shot_dispatch.py` for the dispatch logic.

**Important:** This input must be explicitly forwarded to any reusable workflows called by one-shot.yml. See ci/tripwires.md for the reusable workflow input forwarding pattern.
```

---

#### 9. Update Backend-Specific Test Coverage

**Location:** `docs/learned/testing/dual-backend-testing.md`
**Action:** UPDATE
**Source:** [PR #7740]

**Draft Content:**

```markdown
<!-- Add section on workflow input testing -->

## Workflow Input Testing Across Backends

When workflow dispatch includes backend-specific inputs, tests must verify correct values for both `github` and `draft_pr` backends.

**Pattern:**
- Issue-based plans should assert backend-specific values for the github path
- Draft-PR plans should assert backend-specific values for the draft_pr path
- Both assertions should appear in the same test file for easy comparison

**Example:** See `tests/commands/one_shot/test_one_shot_dispatch.py`:
- `test_dispatch_happy_path()` verifies `inputs["plan_backend"] == "github"`
- `test_dispatch_draft_pr_lifecycle()` verifies `inputs["plan_backend"] == "draft_pr"`

This ensures the CLI correctly determines and passes backend type to the workflow.
```

---

#### 10. Update plan-creation-pathways.md

**Location:** `docs/learned/planning/plan-creation-pathways.md`
**Action:** UPDATE
**Source:** [PR #7740]

**Draft Content:**

```markdown
<!-- Verify lines 26-34 only describe env var routing, remove any config fallback references -->

## Backend Selection

Backend selection is controlled by the `ERK_PLAN_BACKEND` environment variable:
- `"github"`: Issue-based plans (default)
- `"draft_pr"`: Draft-PR-based plans

The environment variable is set by the workflow dispatch chain and there is no config file fallback. If the variable is not set, "github" is used.

See `packages/erk-shared/src/erk_shared/plan_store/__init__.py` for the implementation.
```

---

### LOW Priority

#### 11. Task vs Todo Tool Inconsistency

**Location:** `docs/learned/planning/plan-implement-workflow.md` or `.claude/commands/erk/plan-implement.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
<!-- Clarify task management tool usage -->

## Task Management Tools

During plan implementation, task management is handled via the appropriate tool:
- **TaskCreate/TaskUpdate**: Newer interface for session task tracking
- **TodoWrite**: Alternative interface shown in some documentation examples

Both tools serve similar purposes. Sessions may use either based on which is available or preferred. Documentation should not prescribe one over the other unless there's a clear technical reason.

Note: This observation emerged from session analysis - the implementation used TaskCreate while documentation examples showed TodoWrite.
```

---

#### 12. Idempotent Cleanup Operations Pattern

**Location:** Merge into `docs/learned/commands/multi-path-command-refactoring.md`
**Action:** CREATE (merged with item 6)
**Source:** [Impl]

**Draft Content:**

```markdown
<!-- Include as a section in multi-path-command-refactoring.md -->

## Idempotent Cleanup Operations

When placing cleanup operations at convergence points, ensure they are idempotent:

**Pattern:**
```bash
# Idempotent directory removal
if [ -d .erk/impl-context/ ]; then
  rm -rf .erk/impl-context/
fi
```

**Why idempotency matters:**
- Safe to call from multiple code paths without guards
- Enables placement at convergence points
- Reduces conditional complexity

**Anti-pattern:**
```bash
# Non-idempotent - fails if directory doesn't exist
rm -rf .erk/impl-context/  # May fail or behave unexpectedly
```

See `.claude/commands/erk/plan-implement.md` Step 2d for the cleanup implementation.
```

---

#### 13. Update schema-driven-config.md

**Location:** `docs/learned/configuration/schema-driven-config.md`
**Action:** UPDATE
**Source:** [PR #7740]

**Draft Content:**

```markdown
<!-- Verify no examples reference plan_backend field - if any exist, remove them -->

Note: The `plan_backend` field was removed from GlobalConfig in PR #7740. Backend selection is now controlled exclusively via the `ERK_PLAN_BACKEND` environment variable.

If any examples in this document reference `global_config.plan_backend`, they should be removed or updated to show environment variable usage instead.
```

---

## Contradiction Resolutions

No contradictions found. All existing documentation accurately describes the current implementation. The planned change (env-var-only resolution) is a simplification that affects 4 documents, but these require updates after landing, not contradiction resolution.

---

## Stale Documentation Cleanup

No stale documentation detected at this time. However, **4 documents will become stale after PR #7740 lands** and are addressed in the HIGH/MEDIUM priority documentation items above:

1. `docs/learned/planning/draft-pr-plan-backend.md` - Remove three-tier resolution description
2. `docs/learned/configuration/config-layers.md` - Remove plan_backend from GlobalConfig enumeration
3. `docs/learned/planning/plan-creation-pathways.md` - Ensure no config fallback references
4. `docs/learned/configuration/schema-driven-config.md` - Remove any plan_backend examples

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Empty PR from Draft-PR One-Shot Dispatch

**What happened:** One-shot dispatches for draft-PR plans created empty PRs because the implementation phase used the wrong branch.

**Root cause:** GitHub Actions reusable workflow input defaults do NOT apply when the input is omitted from the caller's `with:` block. The `plan_backend` input was omitted from `one-shot.yml`'s call to `plan-implement.yml`, so the value became empty/null instead of "github", which triggered the `draft_pr` code path check to fail silently and use the wrong branch.

**Prevention:** Always explicitly forward critical inputs in reusable workflow calls. Add tripwire to ci/tripwires.md.

**Recommendation:** TRIPWIRE

### 2. Impl-Context Directory Leaked to PR

**What happened:** The `.erk/impl-context/` directory was not cleaned up during implementation, appearing in the PR diff.

**Root cause:** The cleanup step was placed in Path E (fresh plan save) of the `plan-implement.md` command, but Paths A/B/C/D (existing `.impl/` folders) skip to Step 3, bypassing cleanup.

**Prevention:** Place operations that must run unconditionally at convergence points where all paths merge, not in conditional branches.

**Recommendation:** TRIPWIRE

### 3. Git Push Rejection After PR Review

**What happened:** `git push` failed with non-fast-forward error after addressing PR review comments.

**Root cause:** The remote branch had diverged because an earlier `erk pr submit` created commits, while the local branch had new commits from the review address.

**Prevention:** Use the sync-divergence skill pattern: fetch -> diagnose (check both sides) -> rebase -> re-track -> restack -> submit.

**Recommendation:** ADD_TO_DOC (already documented in erk/tripwires.md)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Reusable Workflow Input Forwarding

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** When calling reusable workflows in GitHub Actions
**Warning:** All critical inputs must be explicitly forwarded in the `with:` block. Do not rely on defaults in the called workflow - if an input is omitted from the caller's `with:` block, the value becomes empty/null instead of using the called workflow's default.
**Target doc:** `docs/learned/ci/tripwires.md`

This is tripwire-worthy because the behavior is counterintuitive (most developers expect defaults to apply), it affects all reusable workflow calls (not just this specific case), and failures are silent (wrong code path executes without error messages). The bug manifests far from its cause - an empty PR appears during implementation, not during dispatch.

### 2. Draft-PR Backend Misconfiguration

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** When modifying one-shot dispatch or plan-implement workflow inputs
**Warning:** The `plan_backend` input must flow through the entire workflow chain (CLI -> workflow_dispatch -> reusable workflow -> environment variable). Missing propagation causes draft-PR plans to be implemented on wrong branches.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because the backend propagation spans 4 layers (CLI, dispatch, reusable workflow, env var), each maintained by potentially different developers. Missing any link breaks the chain silently. The verification checklist provides a concrete way to audit the complete chain.

### 3. Impl-Context Cleanup Path Bug

**Score:** 5/10 (Non-obvious +2, Destructive potential +2, Repeated pattern +1)
**Trigger:** When implementing draft-PR plans or modifying plan-implement command paths
**Warning:** Cleanup operations must execute unconditionally for all paths. Place cleanup at convergence points where all paths merge.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because multi-path commands are common in erk (plan-implement has 5 paths), operations that seem to run "always" may only run on some paths, and the symptom (leaked directory) is subtle and may not be caught in review.

### 4. Git Divergence After PR Review

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When git push fails with non-fast-forward after PR review address
**Warning:** Use sync-divergence skill pattern: fetch -> diagnose both sides -> rebase -> re-track -> restack -> submit.
**Target doc:** Already documented in `docs/learned/erk/tripwires.md`

This item is already documented per session analysis. Including here for completeness but no new tripwire needed.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Test Coverage for Workflow Inputs

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Automated PR review correctly caught missing assertions, suggesting the pattern is well-known enough that tooling catches it. If the pattern repeats (workflow input tests missing assertions), consider promotion. Currently, the tooling serves as an effective backstop.

### 2. Workflow Input Propagation in Multi-Stage Pipelines

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Already covered by item #1 (reusable workflow forwarding) at a higher level of abstraction. This is a specific instance of that general pattern. No separate tripwire needed - the general tripwire covers this case.
