# Documentation Plan: Fix silent plan-header metadata loss during PR submit

## Context

This plan captures documentation needs from PR #8150, which fixed a critical silent bug in the submit pipeline. The bug caused plan-header metadata to be silently lost every time a planned PR was resubmitted. The root cause was a timing issue: `gt submit` overwrites the PR body before `finalize_pr()` could read the metadata, resulting in lost metadata and malformed PR bodies with duplicate plan sections.

The fix introduced a **capture-before-overwrite pattern**: a new pipeline step (`capture_existing_pr_body()`) saves the PR body before any external tool can modify it. This pattern is broadly applicable whenever pipelines interact with external tools that may destructively modify shared state. Additionally, the PR improved terminology by renaming `extract_metadata_prefix()` to `extract_plan_header_block()` and simplifying the `assemble_pr_body()` API.

This documentation matters because the bug was silent (no exceptions, just gradually degrading output) and the fix pattern is cross-cutting: any pipeline interacting with external tools faces similar risks. Future agents working on submit pipelines, external tool integrations, or planned-PR features need to understand both the specific fix and the general pattern.

## Raw Materials

PR #8150

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 14 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score >= 4) | 4 |
| Potential tripwires (score 2-3) | 3 |

## Documentation Items

### HIGH Priority

#### 1. Update docs for function rename: extract_metadata_prefix to extract_plan_header_block

**Location:** `docs/learned/architecture/pr-body-assembly.md`, `docs/learned/planning/planned-pr-lifecycle.md`
**Action:** UPDATE_REFERENCES
**Source:** [PR #8150]

**Draft Content:**

```markdown
## Changes Required

1. Replace all references to `extract_metadata_prefix()` with `extract_plan_header_block()`
2. Update parameter documentation: `metadata_prefix: str` is now `existing_pr_body: str` in `assemble_pr_body()`
3. Add cross-reference to new silent-metadata-loss-planned-pr.md
4. Update tripwire text to explain the silent failure mode (metadata loss results in duplicate plan sections, not exceptions)

## Terminology Note

"plan_header_block" replaces "metadata_prefix" to clarify what is being extracted: the complete header block containing plan metadata (HTML comment + separator), not just a generic prefix.

See `packages/erk-shared/src/erk_shared/plan_store/planned_pr_lifecycle.py` for the renamed function.
```

---

#### 2. Document silent metadata loss bug pattern

**Location:** `docs/learned/planning/silent-metadata-loss-planned-pr.md`
**Action:** CREATE
**Source:** [PR #8150]

**Draft Content:**

```markdown
---
read-when: working on PR submit pipeline, finalize_pr, planned-PR backend, external tool interactions
category: planning
---

# Silent Metadata Loss in Planned PR Submit

## Symptom

Plan-header metadata disappears from PR body on resubmit. Each submit appends duplicate plan sections and footers. PR body grows with repeated content while metadata block is lost.

## Root Cause: Timing Bug

The submit pipeline had a data dependency violation:

1. `PlannedPRBackend.create_plan()` creates draft PR with metadata in body
2. User runs `erk pr submit`
3. `gt submit` **overwrites entire PR body** with commit message
4. `finalize_pr()` reads PR body → metadata already gone
5. `assemble_pr_body()` falls through to wrong format (no metadata = wrong code path)
6. Each subsequent submit compounds the problem

## The Fix: Capture-Before-Overwrite

New pipeline step `capture_existing_pr_body()` saves the PR body BEFORE any external tool can modify it.

Pipeline order (critical):
- `capture_existing_pr_body()` - saves state.existing_pr_body
- `push_and_create_pr()` - calls gt submit (destroys original body)
- `finalize_pr()` - uses pre-captured body from state

## Prevention

1. Always capture data before calling external tools that may overwrite it
2. Use frozen dataclass fields to thread captured data through pipeline
3. Consider validation to detect missing required data (fail fast, not silent)
4. Test metadata preservation through full pipeline cycles

## Source Pointers

- See `capture_existing_pr_body()` in `src/erk/cli/commands/pr/submit_pipeline.py`
- See `_submit_pipeline()` tuple for step ordering
- See `tests/unit/cli/commands/pr/submit_pipeline/test_capture_existing_pr_body.py` for test patterns

## Related

- pr-body-assembly.md (assemble_pr_body API)
- planned-pr-lifecycle.md (extract_plan_header_block function)
- pr-submit-pipeline.md (pipeline architecture)
```

---

#### 3. Update PR submit pipeline documentation

**Location:** `docs/learned/cli/pr-submit-pipeline.md`
**Action:** UPDATE
**Source:** [PR #8150]

**Draft Content:**

```markdown
## Updates Needed

### Add New Pipeline Step

Add `capture_existing_pr_body` as Step 7 (before push_and_create_pr):

**Step 7: capture_existing_pr_body**
- Purpose: Preserve PR body before external tools overwrite it
- When: Only for existing PRs (no-op for new PRs)
- State mutation: Sets `state.existing_pr_body` to full PR body text
- Critical: Must run BEFORE any step that calls external tools (gt, gh)

### Update finalize_pr Documentation

Step 8 (finalize_pr) now:
- Uses pre-captured `state.existing_pr_body` instead of re-reading PR
- Backend detection still determines format (planned vs issue-based)
- Planned-PR backend extracts plan-header block from captured body

### Pipeline Ordering Diagram

```
validate_environment
    |
determine_pr_strategy
    |
[backend-specific steps]
    |
capture_existing_pr_body  <-- NEW: capture before destructive ops
    |
push_and_create_pr        <-- Calls gt submit (destructive)
    |
finalize_pr               <-- Uses captured data
```

### Cross-Reference

See silent-metadata-loss-planned-pr.md for the bug this ordering prevents.
```

---

### MEDIUM Priority

#### 4. Document SubmitState field addition pattern

**Location:** `docs/learned/testing/submit-pipeline-testing.md`
**Action:** CREATE
**Source:** [PR #8150]

**Draft Content:**

```markdown
---
read-when: adding fields to SubmitState, testing submit pipeline steps, modifying pipeline architecture
category: testing
---

# Submit Pipeline Testing Patterns

## SubmitState Construction

All submit pipeline test files use a `_make_state()` helper function with defaults for optional fields.

When adding a new field to `SubmitState`:
1. Add field to the frozen dataclass in `src/erk/cli/commands/pr/submit_pipeline.py`
2. Update `_make_state()` helpers in ALL test files (typically 10+ files)
3. Provide sensible default (usually empty string or None)
4. Update `make_initial_state()` with the default value

## Testing Pipeline Steps in Isolation

Pattern: construct minimal state -> call step -> verify state mutation

Example for `capture_existing_pr_body`:
- Test with existing PR (should capture body)
- Test with no PR for branch (should no-op)
- Test with empty body (should handle gracefully)

## Field Addition Impact

PR #8150 added `existing_pr_body` field, requiring updates to 11 test files. This is expected maintenance cost for frozen dataclass state threading.

Design principle: Minimize state fields to reduce test maintenance burden.

## Source Pointers

- See test file structure in `tests/unit/cli/commands/pr/submit_pipeline/`
- See `_make_state()` pattern in any test file in that directory
```

---

#### 5. Document str.removesuffix() as preferred pattern

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [PR #8150]

**Draft Content:**

```markdown
## String Manipulation Patterns (add new section)

### Use removesuffix/removeprefix (Python 3.9+)

Erk targets Python 3.10+. Use modern string methods instead of manual patterns.

**Preferred:**
```python
text = filename.removesuffix(".md")
```

**Avoid:**
```python
if filename.endswith(".md"):
    text = filename[:-3]
```

The stdlib methods are:
- More readable (intent is clear)
- Safer (no off-by-one errors in slice calculation)
- Consistent (same pattern for suffix and prefix)
```

---

#### 6. Document variable declaration proximity principle

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [PR #8150]

**Draft Content:**

```markdown
## Variable Declaration (add to existing section)

### Declare Variables Close to Use

Principle: Minimize the distance between variable declaration and use.

**Preferred:** Inline when used once
```python
# Use ternary directly in call
return format_output(
    "yes" if condition else "no"
)
```

**Avoid:** Intermediate variable for single use
```python
# Unnecessary intermediate
result = "yes" if condition else "no"
return format_output(result)
```

**Exception:** Extract variables when:
- Name adds significant clarity to a complex expression
- Value is used multiple times
- Expression is deeply nested
```

---

#### 7. Document discussion comment lifecycle in PR operations

**Location:** `docs/learned/pr-operations/discussion-comment-handling.md`
**Action:** CREATE
**Source:** [PR #8150]

**Draft Content:**

```markdown
---
read-when: addressing PR review comments, working with bot summary comments, resolving GitHub threads
category: pr-operations
---

# PR Discussion Comment Handling

## Comment Types

1. **Inline review comments**: Attached to specific code lines, have resolve button
2. **Discussion comments**: Top-level, no resolve button
3. **Bot summary comments**: Discussion comments that reference inline comments

## Resolution Patterns

### Inline Threads
Use `erk exec resolve-review-threads` with JSON stdin for batch resolution.

### Discussion Comments
Must reply explicitly - no "resolve" mechanism exists.

### Bot Summary Comments
Key insight: Bot summary comments need explicit replies EVEN AFTER the inline threads they reference are resolved. The summary exists as a separate discussion thread.

## Workflow Example

1. Fix code issues from inline review comments
2. Commit changes
3. Batch-resolve inline threads via `resolve-review-threads`
4. Reply to any discussion comments (including bot summaries)

## Source Pointer

See `pr-operations` skill for complete command reference.
```

---

#### 8. Investigate pr rewrite metadata preservation

**Location:** `docs/learned/cli/pr-rewrite.md`
**Action:** INVESTIGATE
**Source:** [PR #8150]

**Draft Content:**

```markdown
## Investigation Needed

The `erk pr rewrite` command shares utilities with the submit pipeline:
- Uses `assemble_pr_body()` from shared.py
- May call external tools that modify PR body

**Questions to answer:**
1. Does pr rewrite have the same metadata loss vulnerability?
2. If not, what protection mechanism does it use?
3. Should it adopt the capture-before-overwrite pattern?

**Action:** Review `src/erk/cli/commands/pr/rewrite_cmd.py` and document findings.
```

---

### LOW Priority

#### 9. Document CI failure triage pattern

**Location:** `docs/learned/pr-operations/ci-failure-triage.md`
**Action:** CREATE
**Source:** [PR #8150]

**Draft Content:**

```markdown
---
read-when: CI fails during PR address, distinguishing related vs unrelated failures
category: pr-operations
---

# CI Failure Triage During PR Operations

## Principle

Not all CI failures are caused by your changes. Before investigating, determine if the failure is related.

## Triage Steps

1. Review all CI check results (not just the failed one)
2. If lint/format/types/tests pass but one check fails, investigate that specific check
3. Compare failure to recent main branch CI results
4. If failure exists on main, it's pre-existing (not your problem)

## Decision Matrix

| Core checks (lint, format, types, unit tests) | Other checks | Action |
|-----------------------------------------------|--------------|--------|
| Pass | Fail | Proceed if failure is pre-existing |
| Fail | Any | Fix the failure first |

## Documentation

When proceeding despite CI failure:
- Note the unrelated failure in commit message or PR comment
- Reference that main branch has same failure if applicable
```

---

#### 10. Document test coverage expectations for refactoring vs logic changes

**Location:** `docs/learned/testing/refactoring-test-expectations.md`
**Action:** CREATE
**Source:** [PR #8150]

**Draft Content:**

```markdown
---
read-when: determining test coverage for PR, reviewing PRs for test adequacy
category: testing
---

# Test Coverage Expectations

## Refactoring vs Logic Changes

**Refactoring** (no new tests needed):
- Function/variable renames
- Moving code between files
- Signature changes (parameter renames)
- Import updates

**Logic changes** (tests required):
- New functions/methods
- New code paths
- Behavior changes
- Bug fixes

## PR #8150 Example

- 7 files: refactoring (function rename, signature update) - existing tests sufficient
- 1 file: new logic (`capture_existing_pr_body`) - new test file required
- 11 files: mechanical test updates (adding default field value)

## Self-Review Checklist

Before submitting:
1. Identify which changes are refactoring vs logic
2. Verify new logic has corresponding tests
3. Verify refactoring doesn't break existing tests
```

---

#### 11. Create developer self-review checklist from bot patterns

**Location:** `docs/learned/review/bot-review-checklist.md`
**Action:** CREATE
**Source:** [PR #8150]

**Draft Content:**

```markdown
---
read-when: preparing PR for review, self-reviewing before submit
category: review
---

# Developer Self-Review Checklist

Patterns the review bot checks that you can catch first:

## Python Patterns
- [ ] Using `removesuffix()`/`removeprefix()` instead of manual slice?
- [ ] Variables declared close to use (no unnecessary intermediates)?
- [ ] LBYL pattern (checking before acting, not try/except)?

## Test Coverage
- [ ] New logic has corresponding tests?
- [ ] Refactoring verified by existing tests?

## Documentation
- [ ] Breaking API changes documented?
- [ ] New tripwire-worthy patterns identified?

## PR Operations
- [ ] CI failures investigated (related vs pre-existing)?
- [ ] All review threads addressed (including discussion comments)?
```

---

## Stale Documentation Cleanup

Existing docs with references requiring update after function rename:

### 1. pr-body-assembly.md phantom references

**Location:** `docs/learned/architecture/pr-body-assembly.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `extract_metadata_prefix()` (renamed to `extract_plan_header_block()`)
**Cleanup Instructions:** Find and replace all occurrences of the old function name. Update parameter documentation for `assemble_pr_body()` signature change.

### 2. planned-pr-lifecycle.md phantom references

**Location:** `docs/learned/planning/planned-pr-lifecycle.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `extract_metadata_prefix()` (renamed to `extract_plan_header_block()`)
**Cleanup Instructions:** Find and replace the old function name. Add section on metadata preservation failure modes with cross-reference to silent-metadata-loss-planned-pr.md.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Silent Data Loss from External Tool Timing

**What happened:** Metadata was lost because `finalize_pr()` read PR body AFTER `gt submit` had overwritten it.

**Root cause:** Pipeline steps were ordered without considering data dependencies. External tool (`gt submit`) destroyed data that a later step needed.

**Prevention:** Always capture data before calling external tools that may modify it. Use frozen dataclass fields to thread captured data through pipeline. Add explicit step for data capture before destructive operations.

**Recommendation:** TRIPWIRE - This is a cross-cutting pattern applicable to any pipeline with external tool interactions.

### 2. Pre-existing CI Failures Blocking Progress

**What happened:** CI failed on "exec reference docs stale" which was unrelated to the PR changes.

**Root cause:** Documentation generation wasn't triggered by code changes; pre-existing staleness blocked unrelated PRs.

**Prevention:** Triage CI failures by checking if they exist on main branch. Proceed if failure is pre-existing and core checks (lint, format, types, tests) pass.

**Recommendation:** ADD_TO_DOC - Document the triage pattern but not severe enough for tripwire.

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Capture-Before-Destructive-Operation Pattern

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before calling external tools that overwrite data (gt submit, gh pr edit, etc.)
**Warning:** Capture any data that must be preserved BEFORE calling the tool. Use frozen dataclass field to thread captured data through pipeline. Failure is silent - no exception, just lost data.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because: external tools don't know about erk's data needs; they overwrite without warning. The bug was completely silent - no exceptions, just gradually degrading output that accumulated over multiple submits. The pattern applies to any pipeline step that calls external CLIs.

### 2. assemble_pr_body() Requires existing_pr_body for Planned-PR

**Score:** 5/10 (Non-obvious +2, Silent failure +2, External tool quirk +1)
**Trigger:** Before calling assemble_pr_body() with planned-PR backend
**Warning:** Must extract plan-header metadata block from existing PR body using extract_plan_header_block(). Pass full PR body as existing_pr_body parameter. Without it, metadata is silently lost on every PR update.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because: the API accepts empty string without error, but produces wrong output. Silent failure mode makes debugging difficult - PR body looks "kind of right" but accumulates duplicate sections over time.

### 3. Pipeline Step Ordering Dependencies

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before adding steps to pipelines that pass frozen dataclass state
**Warning:** Steps must be ordered to respect data dependencies. Pattern: capture -> destructive-operation -> use-captured-data. See silent-metadata-loss-planned-pr.md for worked example.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because: frozen dataclasses prevent in-place mutation, so dependencies must be explicit in step ordering. Adding a step "in the wrong place" in the tuple can silently break data flow.

### 4. extract_plan_header_block() Must Be Called Before assemble_pr_body()

**Score:** 4/10 (Non-obvious +2, Silent failure +2)
**Trigger:** Before calling assemble_pr_body() for planned-PR backend
**Warning:** Must call extract_plan_header_block() on existing PR body first. The function extracts the metadata block that assemble_pr_body() needs to preserve.
**Target doc:** `docs/learned/planning/tripwires.md`

This could potentially be merged with candidate #2 since they describe the same API requirement from different angles.

---

## Potential Tripwires

Items with score 2-3 (may warrant tripwire status with additional context):

### 1. SubmitState Field Additions Require Test Updates

**Score:** 3/10 (Repeated pattern +1, Cross-cutting +2)
**Notes:** 11 test files updated in this PR. Not yet tripwire-worthy because the pattern is documented and mechanical - follow the established `_make_state()` helper pattern. Could be promoted if future PRs repeatedly forget test updates.

### 2. str.removesuffix() Preferred Over Manual Slice

**Score:** 2/10 (Repeated pattern +1, Non-obvious +1)
**Notes:** Caught twice in this PR during bot review. Not destructive (just code style), so tripwire seems heavy-handed. Better suited as convention documentation.

### 3. Discussion Comments Need Explicit Replies

**Score:** 2/10 (Non-obvious +2)
**Notes:** GitHub-specific behavior that surprised no one in practice - agent handled it correctly. Document in PR operations docs but not tripwire-worthy.

---

## Implementation Guidance

### Phase 1: Reference Updates (Immediate)

Must complete before other documentation to prevent confusion from phantom references:

1. Update `docs/learned/architecture/pr-body-assembly.md`: function rename, signature change
2. Update `docs/learned/planning/planned-pr-lifecycle.md`: function rename
3. Verify no other docs reference `extract_metadata_prefix()` via grep

### Phase 2: Core Bug Documentation (High Priority)

Create the primary postmortem and establish tripwires:

1. Create `docs/learned/planning/silent-metadata-loss-planned-pr.md`
2. Add tripwires to `docs/learned/architecture/tripwires.md`
3. Add tripwires to `docs/learned/planning/tripwires.md`
4. Update `docs/learned/cli/pr-submit-pipeline.md` with new step

### Phase 3: Pattern Documentation (Medium Priority)

Document reusable patterns discovered:

1. Create `docs/learned/testing/submit-pipeline-testing.md`
2. Update `docs/learned/conventions.md` with removesuffix and variable proximity
3. Create `docs/learned/pr-operations/discussion-comment-handling.md`
4. Investigate `pr rewrite` for same vulnerability

### Phase 4: Developer Experience (Low Priority)

Improve self-service documentation:

1. Create `docs/learned/pr-operations/ci-failure-triage.md`
2. Create `docs/learned/testing/refactoring-test-expectations.md`
3. Create `docs/learned/review/bot-review-checklist.md`

---

## Follow-Up Questions

1. **pr rewrite investigation:** Does `erk pr rewrite` have the same metadata loss bug? It shares utilities with submit pipeline.

2. **Validation opportunity:** Should `assemble_pr_body()` validate that existing_pr_body is non-empty when backend is planned-PR? Would convert silent failure to explicit error.

3. **Tripwire consolidation:** Should candidates #2 and #4 (both about assemble_pr_body API requirements) be merged into a single tripwire entry?

4. **Documentation location:** Should Python version features go in conventions.md or a dedicated python-features.md?
