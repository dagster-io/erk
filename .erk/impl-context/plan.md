# Documentation Plan: Fix impl-signal started to include lifecycle_stage transition

## Context

This PR (#7992) fixed a silent metadata bug where `impl-signal started` was not setting the `lifecycle_stage` field in the plan-header metadata. The bug caused plans to appear stuck at "planned" status in the TUI dashboard instead of transitioning to "impl" when implementation began. The root cause was a command consolidation gap: when `impl-signal started` replaced the legacy `mark_impl_started` command, the `lifecycle_stage` field was accidentally omitted from the metadata dict.

The fix was surgical (one line added to the metadata dict), but the debugging session revealed important patterns about metadata serialization format and test assertion precision. The agent initially assumed GitHub issue metadata was JSON-formatted (because the code builds Python dicts), but discovered it's actually YAML-serialized inside HTML `<details>` blocks. This led to test assertion failures that required understanding the serialization layer.

Documentation is needed to prevent future signal handler modifications from missing required metadata fields, and to guide agents writing tests for metadata updates. The metadata format discovery is cross-cutting knowledge that affects any code touching plan-header updates.

## Raw Materials

PR #7992

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 8 |
| Contradictions to resolve | 1 |
| Tripwire candidates (score>=4) | 2 |
| Potential tripwires (score 2-3) | 2 |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. Outdated command reference in lifecycle.md

**Location:** `docs/learned/planning/lifecycle.md` (lines 1043-1052)
**Action:** UPDATE_REFERENCES
**Phantom References:** `mark-impl-started` command (superseded by `impl-signal started`)
**Cleanup Instructions:** Update the Write Points table to reference `impl-signal started` instead of `mark-impl-started`. The table currently shows that `implementing` stage is "Set By" `mark-impl-started`, but this command has been replaced by the unified `impl-signal started` command.

## Documentation Items

### HIGH Priority

#### 1. Update lifecycle.md Write Points table with correct command reference

**Location:** `docs/learned/planning/lifecycle.md` (lines 1043-1052)
**Action:** UPDATE
**Source:** [PR #7992]

**Draft Content:**

```markdown
Update the Write Points table entry:

| Stage          | Set By                  | When                                    |
| -------------- | ----------------------- | --------------------------------------- |
| `implementing` | `impl-signal started`   | Implementation begins (local or remote) |

Note: The stage display name is "implementing" but the storage value is "impl" (post plan #7999 lifecycle collapse). See the Lifecycle Stage Values section above for the mapping.
```

#### 2. Add lifecycle_stage metadata field requirement tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7992]

**Draft Content:**

```markdown
**implementing event signaling in impl_signal.py** → Read [Plan Lifecycle](lifecycle.md) first. ALL signal handlers (started, ended, submitted) must set `lifecycle_stage` in metadata dict. Missing this field causes silent status tracking failures — plans appear stuck at 'planned' instead of transitioning to 'impl'. See `_signal_started()` and `_signal_submitted()` in impl_signal.py for the required pattern.
```

#### 3. Add clarification section for lifecycle stage terminology

**Location:** `docs/learned/planning/lifecycle.md` (after line 1039, in Lifecycle Stage Tracking section)
**Action:** UPDATE
**Source:** [PR #7992]

**Draft Content:**

```markdown
### Storage Values vs Display Names

The lifecycle stage system has two representations:

| Display Name   | Storage Value | Notes |
|----------------|---------------|-------|
| `implementing` | `impl`        | Collapsed from "implementing"/"implemented" per plan #7999 |
| `implemented`  | `impl`        | Same storage value as implementing |

The TUI display shows the friendly names, but code and metadata use the compact storage values. When testing metadata updates, assert on storage values (e.g., `"lifecycle_stage: impl\n"`).

**Historical context:** Plan #7999 collapsed the separate "implementing" and "implemented" stages into a single "impl" storage value. The display layer still shows distinct names based on context (PR state, etc.), but the underlying metadata uses "impl" for both states.
```

#### 4. Add PR feedback classifier validation tripwire

**Location:** `docs/learned/planning/tripwires.md` or `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
**after running pr-feedback-classifier skill** → Validate output completeness. If `informational_count > 0` but no items in `actionable_threads` array, the Haiku classifier may have excluded threads that belong in actionable_threads per SKILL.md spec. Manual inspection needed. Consider using Sonnet for classification tasks with strict schema requirements.
```

### MEDIUM Priority

#### 5. Document YAML metadata serialization format

**Location:** `docs/learned/architecture/metadata-blocks.md` (add new section)
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Serialization Format

Metadata blocks serialize field values as YAML, not JSON. When writing tests or assertions for metadata content, use YAML format:

**Correct assertion pattern:**
```python
# YAML format with trailing newline
assert "lifecycle_stage: impl\n" in updated_body
```

**Incorrect patterns:**
```python
# JSON format (wrong - metadata is not JSON)
assert '"lifecycle_stage": "impl"' in updated_body

# Missing newline (risky - may match partial values)
assert "lifecycle_stage: impl" in updated_body  # Could match "impl" in "implementing"
```

The serialization is handled by `render_metadata_block()` in `erk_shared.gateway.github.metadata.core`. When in doubt, check this function to understand the exact output format.
```

#### 6. Add YAML assertion pattern tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
**testing GitHub issue metadata updates** → Read [Metadata Blocks Reference](../architecture/metadata-blocks.md) first. Use YAML format assertions (`"key: value\n"`) not JSON format (`'"key": "value"'`). Include trailing newline to avoid substring collisions (e.g., "impl" matching "implementing").
```

#### 7. Document plan-mode hybrid command pattern

**Location:** `docs/learned/commands/plan-mode-hybrid-commands.md` (new file if commands/ category exists, otherwise `docs/learned/planning/plan-mode-hybrid-commands.md`)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Plan Mode with Execute-Oriented Commands
read_when:
  - "invoking commands like /erk:pr-address in plan mode"
  - "creating commands that can run in both plan and execute mode"
---

# Plan Mode with Execute-Oriented Commands

Some erk commands are designed for direct execution but can be invoked in plan mode. When this happens, the agent navigates a hybrid workflow.

## Pattern

1. **Create plan** - Agent enters plan mode and drafts implementation steps
2. **Clarify via AskUserQuestion** - User makes decisions (Act vs Dismiss, etc.)
3. **Gather context** - Task/Explore agents investigate needed changes
4. **Exit with implement-now marker** - User chooses "Skip PR and implement here"
5. **Execute changes** - Agent implements directly in current worktree

## Example Commands

- `/erk:pr-address` - Address PR review comments

## When to Use

This pattern is appropriate for small, iterative changes where creating a separate plan PR adds overhead without value. The user's "Skip PR and implement here" choice signals that the change is small enough for direct implementation.
```

### LOW Priority

#### 8. Document discovery pattern for metadata format

**Location:** `docs/learned/testing/tripwires.md` (add to existing section)
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
**writing tests that assert on serialized output** → Before writing assertions, check the `render_*` or `serialize_*` function to understand actual format. Don't assume format based on in-memory representation (dicts serialize to YAML, not JSON in erk metadata).
```

## Contradiction Resolutions

### 1. Lifecycle stage terminology: "implementing" vs "impl"

**Existing doc:** `docs/learned/planning/lifecycle.md` (lines 1030-1039)
**Conflict:** The Stage Values table shows `implementing` as a stage value, but code actually stores `impl`. The table mixes display names with storage values.
**Resolution:** This is not a true contradiction but rather unclear terminology. Add a "Storage Values vs Display Names" section (item #3 above) to clarify that the table shows display names while code uses storage values. The plan #7999 lifecycle collapse combined "implementing" and "implemented" into the single "impl" storage value, but display logic still shows appropriate names based on context.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Missing metadata field in consolidated command

**What happened:** `impl-signal started` was missing the `lifecycle_stage` field that the legacy `mark_impl_started` command had.
**Root cause:** When consolidating multiple commands into `impl_signal.py`, one code path (`_signal_started`) missed a required metadata field.
**Prevention:** When consolidating commands, audit ALL metadata fields from legacy commands. Compare old and new implementations field-by-field.
**Recommendation:** TRIPWIRE (item #2 above)

### 2. Test assertion format mismatch (JSON vs YAML)

**What happened:** Test asserted `'"lifecycle_stage": "impl"'` (JSON format) but the actual body contained `lifecycle_stage: impl\n` (YAML format).
**Root cause:** Agent assumed JSON format based on code that builds Python dicts, without checking the serialization layer.
**Prevention:** Before writing tests for serialized output, check the `render_*` function to understand actual format.
**Recommendation:** ADD_TO_DOC (items #5 and #8 above)

### 3. Classifier output didn't match spec

**What happened:** Haiku classifier excluded an informational thread from `actionable_threads` array despite SKILL.md spec requiring all threads there.
**Root cause:** Haiku model's interpretation of SKILL.md instructions diverged from expected behavior.
**Prevention:** Add validation check after classifier runs; consider using Sonnet for classification tasks with strict schema requirements.
**Recommendation:** TRIPWIRE (item #4 above)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Missing lifecycle_stage field in signal handlers

**Score:** 8/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2, Destructive potential +2)
**Trigger:** When implementing event signaling in impl_signal.py or modifying signal handlers (started, ended, submitted)
**Warning:** ALL signal handlers (started, ended, submitted) must set `lifecycle_stage` in metadata dict. Missing this field causes silent status tracking failures - plans appear stuck at 'planned' instead of transitioning to 'impl'. The field is required for TUI status indicators (`erk dash`).
**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire prevents a particularly insidious bug class: the code runs without errors, but plan status tracking silently fails. Users see plans stuck at "planned" status indefinitely, with no indication of what went wrong. The fix is simple (add one field), but discovering the bug requires noticing the TUI mismatch.

The pattern applies to all signal handlers in `impl_signal.py`. When `_signal_started()` missed the field, `_signal_submitted()` had it correctly - this inconsistency within the same file makes the tripwire even more valuable.

### 2. PR feedback classifier output validation

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** After running pr-feedback-classifier skill
**Warning:** Validate that `len(actionable_threads) + len(discussion_actions) > 0 OR informational_count == 0`. If `informational_count > 0` but no items in actionable arrays, the Haiku classifier may have excluded threads that belong in actionable_threads per spec. Manual inspection needed.
**Target doc:** `docs/learned/planning/tripwires.md` or `docs/learned/pr-operations/tripwires.md`

The classifier is used by multiple commands (pr-address, pr-review, etc.), making this a cross-cutting concern. When Haiku deviates from the SKILL.md spec, threads are silently dropped and the agent doesn't know to handle them.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Test assertion format assumption (JSON vs YAML)

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Agents assume JSON from in-memory dict representation, but serialization is YAML. Score: 3. May not reach full tripwire threshold because proper test reading prevents this. However, if this pattern recurs, consider promotion.

### 2. Command consolidation metadata audit

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** When replacing old commands with unified commands, audit all metadata fields. Score: 3. Pattern emerged from this PR's bug. If more consolidation work happens and similar bugs appear, promote to full tripwire.

## Code Improvements (Out of Scope for Learn)

The gap analysis identified two items that belong in code rather than documentation:

1. **Lifecycle stage values catalog** - Consider a Literal type or Enum for `("planned", "impl", "prompted", etc.)`. Currently string literals scattered across code.

2. **Docstring for render_metadata_block()** - Add comprehensive docstring documenting the YAML serialization format and output structure.

These are code improvements, not documentation tasks, and should be tracked separately if desired.
