# Documentation Plan: Collapse implementing/implemented into single impl lifecycle stage

## Context

This plan documents a significant schema evolution in erk's plan lifecycle management. The core change collapses two distinct lifecycle stages ("implementing" and "implemented") into a single unified "impl" stage. Previously, plans transitioned through "implementing" (yellow, in-progress) to "implemented" (cyan, ready for merge). Now, all implementation activity uses a single "impl" stage with visual indicators (emojis) distinguishing draft from ready-to-merge states.

This consolidation simplifies both the codebase and the mental model for agents working with plan metadata. The backwards compatibility strategy mirrors the pattern established in schema-v3-migration.md (steps to nodes): the parser accepts old values for existing plans while all new writes use the canonical "impl" value. This design evolution affects exec scripts, display logic, validation, and test assertions across 21 files.

Documentation is essential here because future agents modifying lifecycle-related code need to understand: (1) why old values appear in existing plan metadata, (2) the write discipline requiring "impl" for all new metadata writes, and (3) the three-phase migration pattern that enables backwards compatibility without breaking existing plans. Without this documentation, an agent might incorrectly use "implementing" or "implemented" in new code, creating inconsistency in plan metadata.

## Raw Materials

(No gist URL provided)

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 9     |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 1     |

## Documentation Items

### HIGH Priority

#### 1. Lifecycle Stage Consolidation Migration Doc

**Location:** `docs/learned/planning/lifecycle-stage-consolidation.md`
**Action:** CREATE
**Source:** [PR #7999]

**Draft Content:**

```markdown
---
title: Lifecycle Stage Consolidation
read_when:
  - "working with lifecycle_stage metadata field"
  - "modifying exec scripts that write plan metadata"
  - "encountering implementing or implemented values in existing plans"
tripwires:
  - action: "writing lifecycle_stage value in exec scripts or plan metadata"
    warning: "Always write 'impl' (not 'implementing' or 'implemented'). Validation accepts old values for backwards compatibility but never writes them."
    score: 6
---

# Lifecycle Stage Consolidation

The plan lifecycle stage was consolidated from two stages to one.

## What Changed

| Before              | After  |
| ------------------- | ------ |
| `implementing`      | `impl` |
| `implemented`       | `impl` |

## Why Consolidate

The two-stage model (implementing/implemented) added complexity without clear benefit:
- Agents already use draft/ready PR state for merge readiness
- Color distinction (yellow vs cyan) duplicated the draft/ready signal
- Two stages meant two write points to maintain

The single "impl" stage simplifies the model. Visual indicators (rocket emoji for ready-to-merge) now communicate state that lifecycle_stage previously encoded.

## Backwards Compatibility

### Schema Validation

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py, PlanHeaderSchema.validate -->

See `PlanHeaderSchema.validate()` in `schemas.py` - accepts "implementing" and "implemented" for existing plans, normalizes to "impl" on read.

### Display Logic

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, compute_lifecycle_display -->

See `compute_lifecycle_display()` in `lifecycle.py` - all impl variants render as yellow.

## Write Point Updates

All exec scripts now write "impl" exclusively:

<!-- Source: src/erk/cli/commands/exec/scripts/mark_impl_started.py -->
<!-- Source: src/erk/cli/commands/exec/scripts/impl_signal.py -->
<!-- Source: src/erk/cli/commands/exec/scripts/handle_no_changes.py -->

- `mark-impl-started` - writes "impl" when implementation begins
- `impl-signal` - writes "impl" on implementation events
- `handle-no-changes` - writes "impl" for no-op completions

## Convention

New code must use "impl" for all lifecycle stage writes. The old values exist only for reading existing metadata from plans created before this migration.

## Related

- [Schema V3 Migration](schema-v3-migration.md) - same pattern (steps to nodes)
- [Plan Lifecycle](lifecycle.md) - full lifecycle documentation
```

---

#### 2. Lifecycle Stage Documentation Update

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE
**Source:** [PR #7999]

**Draft Content:**

Update the lifecycle.md file to reflect the consolidated stage:

1. **Update the "Which Phase Am I In?" table** - replace "implementing" and "implemented" rows with single "impl" row

2. **Add historical note after the table:**
```markdown
**Historical Note:** Prior to PR #7999, lifecycle used two implementation stages: "implementing" (yellow) and "implemented" (cyan). These were consolidated into a single "impl" stage. Old values remain valid in existing plan metadata. See [Lifecycle Stage Consolidation](lifecycle-stage-consolidation.md) for migration details.
```

3. **Update tripwire at line 24-26** - change from "Update 3 locations" to "Update 2 locations: LifecycleStageValue type, valid_stages set" (color distinction removed)

4. **Link to migration doc** in the Metadata Block Reference section

---

#### 3. Lifecycle Stage Write Discipline Tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7999]

**Draft Content:**

Add new tripwire entry:

```markdown
- action: "writing lifecycle_stage metadata field in exec scripts"
  warning: "Always write 'impl' (not 'implementing' or 'implemented'). Schema validation accepts old values for backwards compatibility but new writes must use the canonical value."
  score: 6
```

This tripwire is HIGH priority because:
- **Non-obvious (+2):** The type definition shows only "impl" but doesn't explain why old values shouldn't be written
- **Cross-cutting (+2):** Applies to mark-impl-started, impl-signal, handle-no-changes, and any future exec scripts writing lifecycle state
- **Silent failure (+2):** Writing old values doesn't error - schema accepts them - but creates inconsistent metadata

---

#### 4. Resolve Two-Stage Model Contradiction

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE (resolve contradiction)
**Source:** [PR #7999]

The existing lifecycle.md documents the two-stage model as current. After this PR lands, the documentation must reflect:

1. Single "impl" stage is the current model
2. Two-stage model is historical context for existing metadata
3. Cross-reference to lifecycle-stage-consolidation.md for full migration details

This is a design evolution, not a staleness issue. Both docs remain valid during transition, with the migration doc bridging the gap.

---

### MEDIUM Priority

#### 5. Impl-Context Direct Creation Pattern

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE
**Source:** [PR #7999]

**Draft Content:**

Add section documenting the removal of `build_impl_context_files()`:

```markdown
## Direct Disk Creation

Previously, impl-context creation used a two-step pattern:
1. `build_impl_context_files()` returned in-memory dict of file paths to content
2. `commit_files_to_branch()` wrote files to git without disk writes

<!-- Source: packages/erk-shared/src/erk_shared/impl_context.py, create_impl_context -->

Now, `create_impl_context()` writes directly to disk at `.erk/impl-context/`. This simplifies the submit workflow by eliminating the in-memory intermediate step.

**Cleanup requirement unchanged:** After plan-implement, explicit `git rm -rf .erk/impl-context/` is still required.
```

---

#### 6. Submit Error Recovery Pattern

**Location:** `docs/learned/planning/submit-error-recovery.md`
**Action:** CREATE
**Source:** [PR #7999]

**Draft Content:**

```markdown
---
title: Submit Error Recovery
read_when:
  - "debugging submit command failures"
  - "understanding branch state after failed pushes"
---

# Submit Error Recovery

The submit command handles push failures gracefully, keeping users on their original branch.

## Branch Preservation on Failure

<!-- Source: src/erk/cli/commands/submit.py, commit_files_to_branch -->

When push fails, the user remains on their original branch. No rollback is needed because the submit command uses git plumbing (`commit_files_to_branch`) instead of checking out the plan branch. The branch is created and committed to without changing the working directory's HEAD.

## Test Coverage

<!-- Source: tests/commands/submit/test_rollback.py, test_submit_push_failure_leaves_original_branch_intact -->

See `test_submit_push_failure_leaves_original_branch_intact()` - verifies:
- User stays on original branch when push fails
- No plan branch checkout occurred
- No workflow triggered on failure
- No PR created on failure

## Why This Matters

Previous approaches required explicit rollback on failure. The plumbing approach eliminates rollback complexity: if push fails, the user's working directory is unchanged.
```

---

#### 7. Status Indicators Logic Update

**Location:** `docs/learned/planning/status-indicators.md`
**Action:** UPDATE
**Source:** [PR #7999]

**Draft Content:**

Update existing documentation to reflect consolidated indicator logic:

```markdown
## Ready-to-Merge Indicator

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, _build_indicators -->

The rocket emoji indicator now applies to all "impl" variants. Previously, only the "implemented" stage (cyan) showed the rocket. Now, any plan in impl stage can show the ready-to-merge indicator based on PR state.

Stage detection key remains "impl" in the display string. Backwards compatibility ensures old "implemented" values still render correctly (as yellow, with indicator when ready).
```

---

#### 8. Draft PR Lifecycle Stage References

**Location:** `docs/learned/planning/draft-pr-lifecycle.md`
**Action:** UPDATE
**Source:** [PR #7999]

**Draft Content:**

Update references from implementing/implemented to impl:

1. Change any mention of stage progression through "implementing" then "implemented" to reference single "impl" stage
2. Clarify that draft/ready PR distinction is now independent of lifecycle stage value
3. Document that lifecycle_stage remains "impl" throughout the PR's lifecycle, with PR draft state indicating merge readiness

---

#### 9. Test Architecture: Submit Tests Refactor

**Location:** `docs/learned/testing/submit-tests.md`
**Action:** CREATE
**Source:** [PR #7999]

**Draft Content:**

```markdown
---
title: Submit Command Test Patterns
read_when:
  - "writing tests for submit command"
  - "debugging submit test failures"
---

# Submit Command Test Patterns

## Test Focus: Cleanup Over Commit Mechanics

<!-- Source: tests/commands/plan/test_submit.py -->

Submit command tests shifted focus from verifying plumbing commit mechanics to verifying cleanup behavior. Tests now:

1. Use isolated filesystem fixtures
2. Verify `.erk/impl-context/` is cleaned up after submit
3. Verify branch state preservation on failures

## Key Test Patterns

### Cleanup Verification
- Create `.erk/impl-context/` with test content
- Run submit
- Assert directory no longer exists

### Failure Recovery
- Mock push to fail
- Assert original branch unchanged
- Assert no workflow triggered

See `test_submit.py` for implementation examples.
```

---

### LOW Priority

#### 10. Tripwire Update: Lifecycle Stage Renaming

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7999]

**Draft Content:**

Update the existing tripwire at line 179 (approximately):

Change from:
```markdown
- action: "renaming a lifecycle stage value"
  warning: "Update 3 locations: LifecycleStageValue type, valid_stages set, and color conditions in compute_lifecycle_display()."
```

To:
```markdown
- action: "renaming a lifecycle stage value"
  warning: "Update 2 locations: LifecycleStageValue type and valid_stages set. Color conditions were simplified - all impl variants use yellow."
```

The color distinction was removed (cyan eliminated), reducing the update surface from 3 to 2 locations.

---

## Contradiction Resolutions

### 1. Two-Stage vs One-Stage Lifecycle Model

**Existing doc:** `docs/learned/planning/lifecycle.md`
**Conflict:** Existing documentation describes two distinct stages (implementing/implemented with yellow/cyan colors). PR #7999 collapses these to single "impl" stage.
**Resolution:**

This is a genuine design evolution, not staleness. Both documents will coexist:
1. Create `lifecycle-stage-consolidation.md` as the migration reference
2. Update `lifecycle.md` with consolidated stage definition
3. Add historical note explaining the two-stage model was intentional pre-migration
4. Link between documents so agents understand the evolution

The contradiction is resolved by treating it as evolution with backwards compatibility, not as conflicting truths.

---

## Stale Documentation Cleanup

**No stale documentation detected.**

All existing documentation references were verified against current codebase. lifecycle.md references schemas.py and lifecycle.py which exist. schema-v3-migration.md references roadmap.py and metadata_blocks.py which exist.

---

## Prevention Insights

### 1. Schema Evolution with Backwards Compatibility

**What happened:** Consolidating lifecycle stages required maintaining compatibility with existing plans that have "implementing" or "implemented" in their metadata.

**Root cause:** Direct replacement of old values would break parsing of existing plans.

**Prevention:** Follow the three-phase evolution pattern:
1. Parser accepts both old and new values with normalization on read
2. Update all write points to use new canonical value
3. Eventually remove legacy values from validation (after sufficient migration period)

**Recommendation:** TRIPWIRE - This pattern applies to any schema enum modification.

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Lifecycle Stage Write Discipline

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before writing lifecycle_stage metadata field in exec scripts
**Warning:** "Always write 'impl' (not 'implementing' or 'implemented'). Schema validation accepts old values for backwards compatibility but new writes must use the canonical value."
**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire prevents the most likely mistake: an agent seeing "implementing" in existing code or metadata and using it in new code. The schema accepts it silently, creating inconsistent metadata that makes debugging harder.

### 2. Schema Backwards Compatibility Pattern

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before modifying LifecycleStageValue or other metadata schema enums
**Warning:** "Follow three-phase evolution: 1) Parser accepts both old and new values with normalization, 2) Update all write points to use new canonical value, 3) Eventually remove legacy values from validation."
**Target doc:** `docs/learned/architecture/tripwires.md` or `docs/learned/planning/tripwires.md`

This pattern was established in schema-v3-migration.md (steps to nodes) and applied again here. Future schema changes should follow this pattern to avoid breaking existing metadata.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Impl-Context Cleanup Requirement

**Score:** 3/10 (Cross-cutting +2, Silent failure +1)
**Notes:** Explicit `git rm -rf .erk/impl-context/` is required after plan-implement. However, this cleanup requirement is already documented in impl-context.md and is not new to this PR. The failure mode (stale files cause Prettier CI failures) is visible rather than silent. Did not meet threshold because the pattern is well-established and consequences are catchable in CI.

---

## Implementation Roadmap

Recommended sequence for documentation work:

**Phase 1: Resolve Contradictions (HIGH)**
1. Create `lifecycle-stage-consolidation.md` migration doc
2. Update `lifecycle.md` with consolidated stage and historical note
3. Add lifecycle stage write discipline tripwire to `planning/tripwires.md`

**Phase 2: Update Related Docs (MEDIUM)**
4. Update `impl-context.md` with direct creation pattern
5. Create `submit-error-recovery.md` for branch rollback pattern
6. Update `status-indicators.md` for ready-to-merge logic
7. Update `draft-pr-lifecycle.md` stage references

**Phase 3: Complete Test Documentation (MEDIUM-LOW)**
8. Create `submit-tests.md` for test architecture change
9. Update tripwire at line 179 (3 locations changed to 2 locations)

**Phase 4: Consider Schema Evolution Tripwire**
10. Optionally add schema backwards compatibility tripwire to `architecture/tripwires.md`
