# Documentation Plan: Add erk-remote-setup to ErkImplWorkflowCapability bundle declaration

## Context

This plan consolidates learnings from PR #8114, which fixed a bug where the `erk-remote-setup` GitHub Action was bundled in the erk wheel (via `pyproject.toml`) but not registered with the capability sync system. The bug caused CI failures in downstream repositories like `dagster-io/internal` when workflows referenced an action that was never synced to their `.github/actions/` directory.

The implementation sessions revealed several important patterns and error modes. Most significantly, when adding a managed artifact to a Capability class, developers must update **five separate locations** in the class: the docstring, the `artifacts` property, the `managed_artifacts` property, and both the `install()` and `uninstall()` methods. This PR itself demonstrated the failure mode when the plan specified updating all five locations, but the implementation omitted the docstring update. The PR passed all tests and was merged anyway, proving the silent nature of this documentation inconsistency.

Additionally, the implementation sessions uncovered a pre-existing bug in the `setup-impl` command where the auto-detection code path passes a `branch_slug` parameter to a function that does not accept it. Agents can work around this by reading `.impl/plan.md` directly when the folder already exists, but the bug blocks the standard plan-implement workflow.

## Raw Materials

- Session 39e2b66c: Planning session for the bug fix
- Session 2bf10537: Implementation session (parts 1 and 2)
- PR #8114: The bug fix PR

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 7     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Capability 5-Place Update Checklist

**Location:** `docs/learned/capabilities/tripwires.md`
**Action:** CREATE or UPDATE (add section if file exists)
**Source:** [Plan], [Impl], [PR #8114]

**Draft Content:**

```markdown
## Adding Managed Artifacts to Capability Classes

When adding a managed artifact (workflow, action, or config file) to a Capability subclass, you must update **five locations**:

1. **Class docstring** — Add to the "Installs:" list
2. **`artifacts` property** — Add `CapabilityArtifact` entry
3. **`managed_artifacts` property** — Add `ManagedArtifact` entry
4. **`install()` method** — Add to the appropriate list (workflows, actions, or configs)
5. **`uninstall()` method** — Add to the corresponding cleanup list

Missing any location causes either:
- **Documentation inconsistency** (docstring) — Silent failure, no tests catch it
- **Sync failure** (managed_artifacts) — Artifact bundled but not synced to downstream repos

See `src/erk/capabilities/workflows/erk_impl.py` for the canonical example of this pattern in `ErkImplWorkflowCapability`.

### Common Mistake

PR #8114 demonstrates the failure mode: the plan specified all five updates, but implementation omitted the docstring. Tests passed because they validate `artifacts` and `managed_artifacts` properties, not docstring content.
```

---

#### 2. Bundle vs Sync Layer Separation with Concrete Example

**Location:** `docs/learned/architecture/bundled-artifacts.md`
**Action:** UPDATE (expand existing documentation)
**Source:** [Plan], [Impl]

**Draft Content:**

```markdown
## Case Study: erk-remote-setup Bug (PR #8114)

The `erk-remote-setup` action demonstrated the "bundled but not synced" failure mode:

**What happened:**
- Action was listed in `pyproject.toml` under `force-include` (line 90)
- Action was used by 5 workflows: plan-implement, learn, one-shot, pr-address, pr-fix-conflicts
- Action was NOT listed in `ErkImplWorkflowCapability.managed_artifacts`

**Result:**
- Action was packaged into the erk wheel
- When erk synced artifacts to `dagster-io/internal`, the action was skipped
- CI failed with "Can't find 'action.yml' under '.github/actions/erk-remote-setup'"

**Fix:**
Added `ManagedArtifact(name="erk-remote-setup", artifact_type="action")` to `managed_artifacts` property, plus the corresponding entries in install/uninstall methods.

**Lesson:**
Being bundled (`pyproject.toml`) is necessary but not sufficient. Artifacts must also be registered in a Capability's `managed_artifacts` to be synced to downstream repositories.
```

---

#### 3. setup-impl Auto-Detect Branch Slug Bug Workaround

**Location:** `docs/learned/planning/tripwires.md`
**Action:** CREATE or UPDATE (add section)
**Source:** [Impl]

**Draft Content:**

```markdown
## setup-impl Auto-Detect TypeError

When `.impl/` exists with `plan_ref.json` and you run `erk exec setup-impl` without arguments, the auto-detect path may fail with:

```
TypeError: setup_impl_from_issue() got an unexpected keyword argument 'branch_slug'
```

**Root cause:** `_handle_issue_setup()` passes `branch_slug=None` to `setup_impl_from_issue()`, but that function does not accept this parameter. See `src/erk/exec_scripts/setup_impl.py`.

**Workaround:** If `.impl/` already exists and contains valid content:
1. Verify `.impl/plan.md` exists and has the plan content
2. Verify `.impl/plan_ref.json` has correct plan metadata
3. Skip the setup-impl command and read `.impl/plan.md` directly
4. Proceed with implementation as normal

This workaround is valid because the `.impl/` folder was successfully set up in a prior session. The bug only affects re-running setup-impl when tracking is already established.
```

---

### MEDIUM Priority

#### 4. Pre-existing .impl/ Workflow Bypass Pattern

**Location:** `docs/learned/planning/impl-folder.md` or `docs/learned/planning/plan-implement-workflow.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Recovery: Bypassing setup-impl with Pre-existing .impl/

When `setup-impl` fails but `.impl/` already exists with valid content, agents can bypass the setup command entirely:

**Validation checklist before bypassing:**
1. `.impl/` directory exists
2. `.impl/plan.md` contains the plan content
3. `.impl/plan_ref.json` has valid plan metadata (plan_id, issue_url)

**Proceeding with implementation:**
- Read `.impl/plan.md` directly to get plan instructions
- Execute the implementation steps as normal
- Run `erk exec impl-verify` at the end to confirm `.impl/` preservation
- Signal completion with `erk exec impl-signal` commands

This bypass is appropriate when the setup error is unrelated to the current plan (e.g., a pre-existing bug in setup-impl itself).
```

---

#### 5. WIP Commit Handling in Plan Workflow

**Location:** `docs/learned/planning/branch-management.md` or `docs/learned/planning/plan-implement-workflow.md`
**Action:** UPDATE or CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
## WIP Commits and Branch Divergence

During plan setup, the remote branch may receive a "WIP: Prepare for PR submission" commit containing preliminary implementation or `.impl/` setup changes.

**Expected behavior:**
- Local implementation creates commits with the same changes
- After `erk pr submit`, local and remote branches diverge
- Git rebase (`git rebase origin/<branch>`) auto-detects duplicate changes
- Rebase skips local commits that duplicate remote WIP content

**Resolution:**
- Use `git push --force-with-lease` after rebase to sync branches
- Force-push is safe because the remote WIP commit is a staging artifact, not user work

This divergence is expected and recoverable. It does not indicate a problem with the implementation.
```

---

#### 6. Multi-Artifact Pattern Update with erk-remote-setup Example

**Location:** `docs/learned/capabilities/adding-workflows.md` (lines 122-143)
**Action:** UPDATE
**Source:** [Diff]

**Draft Content:**

```markdown
<!-- Update existing multi-artifact examples to include erk-remote-setup -->

As of PR #8114, `ErkImplWorkflowCapability` manages 4 artifacts:
- 1 workflow: `plan-implement.yml`
- 3 actions: `setup-claude-code/`, `setup-claude-erk/`, `erk-remote-setup/`

The `erk-remote-setup` action is shared by all 5 implementation workflows but managed centrally through `ErkImplWorkflowCapability` to avoid duplication across capability declarations.
```

---

#### 7. Shared Action Dependencies Pattern

**Location:** `docs/learned/ci/composite-action-patterns.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

```markdown
## Shared Action Management

When a composite action is used by multiple workflows, assign it to a single capability rather than duplicating across multiple capability declarations.

**Example: erk-remote-setup**
- Used by: plan-implement, learn, one-shot, pr-address, pr-fix-conflicts
- Managed by: `ErkImplWorkflowCapability` only
- Rationale: Centralized management ensures consistent syncing and avoids drift

**Guideline:** Shared actions that support implementation workflows belong in `ErkImplWorkflowCapability`. Workflow-specific actions belong in their respective capability classes.
```

---

## Contradiction Resolutions

None identified. All existing documentation is consistent with the implementation.

## Stale Documentation Cleanup

None identified. All existing documentation references valid code artifacts and file paths.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Bundled Artifact Not Synced

**What happened:** `erk-remote-setup` was in `pyproject.toml` `force-include` but missing from `managed_artifacts`, causing CI failures in downstream repos.
**Root cause:** The bundle layer (pyproject.toml) and sync layer (managed_artifacts) are independent. Both must be updated.
**Prevention:** Consider adding a test that validates pyproject.toml action entries match the union of all Capability `managed_artifacts` with `artifact_type="action"`.
**Recommendation:** ADD_TO_DOC (covered by bundled-artifacts.md case study)

### 2. Incomplete Capability Updates (Missing Docstring)

**What happened:** Plan specified 5 locations to update; implementation did only 4. Docstring was not updated.
**Root cause:** Docstring is visually separated from the implementation code (properties/methods), making it easy to forget.
**Prevention:** Create explicit 5-place checklist as a tripwire. Consider adding a consistency test or linter.
**Recommendation:** TRIPWIRE (score 6)

### 3. setup-impl Auto-Detect TypeError

**What happened:** Running `erk exec setup-impl` with no arguments failed with `branch_slug` TypeError when `.impl/` already existed.
**Root cause:** Function signature mismatch in the auto-detect code path. `_handle_issue_setup()` passes a parameter that `setup_impl_from_issue()` does not accept.
**Prevention:** Add integration test exercising auto-detect from existing `.impl/` with `plan_ref.json`. Fix the function signature.
**Recommendation:** TRIPWIRE (score 5)

### 4. Edit Tool Prerequisite Error

**What happened:** Agent attempted to edit test file after viewing via Grep, which does not satisfy Read requirement.
**Root cause:** Grep output shows file content but does not register as "read" for Edit tool purposes.
**Prevention:** Always use Read tool explicitly before Edit, even after Grep with context flags.
**Recommendation:** ADD_TO_DOC (general tool usage pattern, low severity)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Capability 5-Place Update Checklist

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before adding a managed artifact to a Capability class
**Warning:** Update all 5 locations: class docstring "Installs:" list, `artifacts` property, `managed_artifacts` property, `install()` method actions list, `uninstall()` method actions list. Missing any location causes documentation inconsistency (docstring) or sync failures (managed_artifacts).
**Target doc:** `docs/learned/capabilities/tripwires.md`

This tripwire is critical because the PR that motivated this learn plan itself demonstrates the failure: the docstring update was specified in the plan but omitted from implementation. Tests passed because they do not validate docstring content. The bug was merged silently.

### 2. setup-impl Auto-Detect Branch Slug Bug

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +1)
**Trigger:** When `erk exec setup-impl` fails with `branch_slug` TypeError and `.impl/` already exists
**Warning:** Bypass setup-impl and read `.impl/plan.md` directly if `.impl/` exists and is valid. Check that `.impl/plan.md` and `.impl/plan_ref.json` exist before proceeding.
**Target doc:** `docs/learned/planning/tripwires.md`

This bug blocks the standard plan-implement workflow. The workaround is non-obvious (bypass the failing command entirely rather than trying to fix parameters) and affects all agents implementing plans when `.impl/` already has tracking established.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Bundle vs Sync Layer Separation

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** May reach tripwire threshold if more "bundled but not synced" bugs occur. Currently documented as a case study rather than a tripwire because the 5-place checklist tripwire should catch most cases at the source.

### 2. Pre-existing .impl/ Workflow Bypass

**Score:** 2/10 (Non-obvious +2)
**Notes:** This is a recovery pattern rather than a primary workflow guard. Useful to document in planning docs but does not warrant tripwire-level visibility. The setup-impl bug itself is the real tripwire; this is just the workaround.

## Implementation Gap Tracking

**Critical finding:** The implementation did not complete all plan steps.

- **Plan specified:** Update the class docstring (lines 18-25) to add `.github/actions/erk-remote-setup/` to the "Installs:" list
- **Implementation result:** Docstring was NOT updated; all other 4 locations were updated correctly

**Current state in `src/erk/capabilities/workflows/erk_impl.py` lines 18-25:**
The docstring lists only 3 items (plan-implement.yml, setup-claude-code/, setup-claude-erk/) but should list 4 (including erk-remote-setup/).

**Recommended follow-up:**
1. The docstring gap should be tracked as technical debt
2. Use this PR as the motivating example for the 5-place checklist tripwire
3. Consider adding a test that validates docstring mentions all managed artifacts

## Next Steps

1. **Immediate (HIGH priority):**
   - Add 5-place capability update checklist to `docs/learned/capabilities/tripwires.md`
   - Add setup-impl branch_slug workaround to `docs/learned/planning/tripwires.md`
   - Expand `docs/learned/architecture/bundled-artifacts.md` with erk-remote-setup case study

2. **Short-term (MEDIUM priority):**
   - Update `docs/learned/capabilities/adding-workflows.md` examples to include erk-remote-setup
   - Document pre-existing `.impl/` bypass pattern in `docs/learned/planning/`
   - Document WIP commit handling in `docs/learned/planning/`

3. **Optional (LOW priority):**
   - Create follow-up issue to fix ErkImplWorkflowCapability docstring
   - Consider adding test that validates docstring vs managed_artifacts consistency
