# Documentation Plan: Rename DraftPRPlanBackend → PlannedPRBackend and delete plan migration command

## Context

PR #8038 represents a pure refactoring effort that renamed `DraftPRPlanBackend` to `PlannedPRBackend` and removed the deprecated `plan-migrate-to-draft-pr` command. The rename was systematic, affecting 100 files with 132 individual items renamed across code, tests, documentation, commands, and skills. All existing documentation was comprehensively updated inline with the changes.

While this PR needs no additional documentation for the refactoring itself (all docs were updated inline), the refactoring process revealed valuable meta-patterns worth documenting. The audit-pr-docs bot caught 14 violations during review, exposing systematic documentation debt patterns: stale line numbers, wrong function references, broken links, and stale API patterns in tripwires. These patterns represent cross-cutting concerns that will help future large-scale refactorings succeed with fewer iterations.

The key insight is distinguishing between documenting *what was built* (nothing new - pure refactoring) versus documenting *lessons learned during the process* (how to do systematic renames better). This plan focuses on the latter.

## Raw Materials

See `.erk/scratch/sessions/1bc853ec-4c4b-4bf6-9c7c-89c7e2c051e3/learn-agents/` for analysis files.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 4     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 1     |

## Documentation Items

### HIGH Priority

No HIGH priority items. All contradictions were resolved within PR #8038 itself (7 stale doc references updated or deleted inline).

---

### MEDIUM Priority

#### 1. Documentation Source Pointer Best Practices

**Location:** `docs/learned/documentation/source-pointer-best-practices.md`
**Action:** CREATE
**Source:** [PR #8038]

**Draft Content:**

```markdown
---
read-when:
  - writing source pointer comments in documentation
  - referencing code locations in learned docs
  - updating documentation after code changes
---

# Source Pointer Best Practices

This document covers patterns for writing source pointers that remain accurate as code evolves.

## The Problem: Line Number Drift

Line numbers drift as files grow. In PR #8038, `submit_pipeline.py` grew from 625 to 932 lines, invalidating all line-based references.

## Recommended Pattern: Function-Name-Based Pointers

Use function or class names as anchors instead of line numbers:

Good: `See src/erk/gateway/gh.py, specifically the run_gh_command function`
Bad: `See src/erk/gateway/gh.py:1588`

## When Line Ranges Are Acceptable

Short-lived documentation (PR descriptions, commit messages) can use line ranges since they are point-in-time snapshots.

## Source Pointer Format

Follow the patterns in `docs/learned/documentation/source-pointers.md` for formal reference syntax.

## Tripwires

- Before adding source pointer comments to documentation, use function-name-based pointers instead of line numbers
```

---

#### 2. Systematic Rename Checklist

**Location:** `docs/learned/refactoring/systematic-rename-checklist.md`
**Action:** CREATE
**Source:** [PR #8038]

**Draft Content:**

```markdown
---
read-when:
  - performing a systematic rename across many files
  - renaming a class, function, or concept codebase-wide
  - planning a large refactoring effort
---

# Systematic Rename Checklist

This checklist ensures comprehensive coverage when renaming concepts across the codebase. Derived from PR #8038 which renamed 132 items across 100 files.

## Pre-Rename: Scope Assessment

- [ ] Identify all locations: classes, functions, modules, variables, type literals
- [ ] Distinguish user-facing terminology from internal implementation details
- [ ] Determine backward compatibility requirements (serialized formats, APIs)

## Rename Locations

### Code
- [ ] Class definitions
- [ ] Function definitions
- [ ] Module file names
- [ ] Variable names
- [ ] Type annotations and literals
- [ ] Import statements
- [ ] Docstrings (often missed!)

### Tests
- [ ] Test file names
- [ ] Test function names
- [ ] Test fixture names
- [ ] Helper function names

### Documentation
- [ ] Documentation file names
- [ ] Cross-reference links
- [ ] Section headings (often missed!)
- [ ] Code examples
- [ ] Tripwire messages

### Commands and Skills
- [ ] Command file names
- [ ] Command descriptions
- [ ] Skill references

## Post-Rename: Verification

- [ ] Run audit-pr-docs bot iteratively during PR
- [ ] Search for old terminology in all text files
- [ ] Verify all cross-reference links resolve

## Example: User-Facing vs Internal

From PR #8038:
- Renamed: `DraftPRPlanBackend` → `PlannedPRBackend` (user-facing class name)
- Preserved: `"github-draft-pr"` (internal serialized provider ID for backward compatibility)
```

---

#### 3. Audit Bot Violation Patterns

**Location:** `docs/learned/documentation/audit-bot-violation-patterns.md`
**Action:** CREATE
**Source:** [PR #8038]

**Draft Content:**

```markdown
---
read-when:
  - audit-pr-docs bot reports violations
  - writing documentation that references code
  - debugging stale documentation
---

# Audit Bot Violation Patterns

The audit-pr-docs bot catches documentation drift. This document catalogs common violation patterns and how to avoid them.

## Common Violation Types

### 1. Stale Line Numbers (Most Common)

**Pattern:** `see line 1588` becomes invalid as code grows
**Fix:** Use function names as anchors instead
**Example:** `See the run_gh_command function in gh.py`

### 2. Wrong Function Names

**Pattern:** Prose references functions that were renamed
**Fix:** Search for the exact function name before referencing

### 3. Wrong Paths

**Pattern:** Documentation claims path is `.erk/plan/PLAN.md` when actual path is `.erk/impl-context/plan.md`
**Fix:** Verify paths exist before documenting

### 4. Broken Links

**Pattern:** Links to files that were renamed without updating references
**Fix:** Search for links to any renamed file

### 5. Stale API Patterns in Tripwires

**Pattern:** Tripwire warning references detection mechanism that changed
**Fix:** Update tripwire messages when referenced APIs change

## Prevention Strategy

1. Write documentation with function-name anchors, not line numbers
2. Run audit bot iteratively during PR development
3. After renames, search for all references to renamed items
```

---

### LOW Priority

#### 4. Backend Detection Evolution

**Location:** `docs/learned/architecture/backend-detection-evolution.md`
**Action:** CREATE
**Source:** [PR #8038]

**Draft Content:**

```markdown
---
read-when:
  - updating tripwires that reference detection patterns
  - changing how plan backends are identified
  - debugging backend type detection
---

# Backend Detection Evolution

This document explains how plan backend detection has evolved, to help maintain accurate tripwires.

## Evolution Summary

Backend detection moved from inspecting `header_fields.get(BRANCH_NAME)` to using `get_provider_name()` dispatch.

## Why Detection Changed

The provider dispatch pattern is more reliable and follows the standard polymorphic design used elsewhere in erk.

## Impact on Tripwires

Tripwires referencing the old detection pattern become stale when the detection mechanism changes. Update tripwire messages when referenced APIs change.

See `packages/erk-shared/src/erk_shared/plan_store/` for current backend implementation.
```

---

## Contradiction Resolutions

All 7 contradictions were STALE_DOC instances resolved within PR #8038 itself:

| Contradiction | Resolution |
|---------------|------------|
| `docs/learned/planning/draft-pr-plan-backend.md` | RENAMED to `planned-pr-backend.md`, content updated |
| `docs/learned/planning/plan-creation-pathways.md` | Updated to "Planned-PR (PlannedPRBackend)" |
| `docs/learned/planning/plan-migrate-to-draft-pr.md` | DELETED (command removed) |
| `.claude/commands/erk/migrate-plan-to-draft-pr.md` | DELETED (command removed) |
| `docs/learned/testing/environment-variable-isolation.md` | Updated to `ERK_PLAN_BACKEND="planned_pr"` |

**Conclusion:** No additional work needed. All contradictions resolved inline.

## Stale Documentation Cleanup

**None.** All stale documentation was updated or deleted within PR #8038:

| Doc | Action Taken |
|-----|--------------|
| `docs/learned/planning/draft-pr-plan-backend.md` | RENAMED + UPDATED |
| `docs/learned/planning/draft-pr-lifecycle.md` | RENAMED + UPDATED |
| `docs/learned/planning/plan-migrate-to-draft-pr.md` | DELETED |
| `.claude/commands/erk/migrate-plan-to-draft-pr.md` | DELETED |

## Prevention Insights

### 1. Line Number Drift in Documentation

**What happened:** Documentation referenced specific line numbers that became stale as code grew. In one case, `submit_pipeline.py` grew from 625 to 932 lines.

**Root cause:** Line numbers are point-in-time references that don't survive code evolution.

**Prevention:** Use function-name-based pointers. Instead of "see line 1588", write "see the run_gh_command function".

**Recommendation:** TRIPWIRE - This is a cross-cutting, non-obvious pattern.

### 2. Docstrings Lagging Renames

**What happened:** Several docstrings still referenced old function/class names after the rename.

**Root cause:** Docstrings are often not covered by automated rename tools and are easy to miss in manual review.

**Prevention:** Include docstrings in systematic rename checklists. Search for old terminology in all text strings.

**Recommendation:** ADD_TO_DOC - Part of systematic rename checklist.

### 3. Tripwire Messages with Stale API References

**What happened:** Tripwire warning messages referenced `header_fields.get(BRANCH_NAME)` detection pattern that had been replaced.

**Root cause:** Tripwires describe behavior but aren't automatically updated when the behavior they describe changes.

**Prevention:** When changing API patterns, search for tripwires that reference the old pattern.

**Recommendation:** ADD_TO_DOC - Note in backend detection doc.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Documentation Source Pointers Drift

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)

**Trigger:** Before adding source pointer comments to documentation

**Warning:** "Use function-name-based pointers (`See file.py, function_name`) instead of line-based pointers (`file.py:123`). Line numbers drift as code grows. Example from PR #8038: submit_pipeline.py grew 625 to 932 lines, invalidating all line-based references."

**Target doc:** `docs/learned/documentation/source-pointer-best-practices.md`

This is tripwire-worthy because the failure mode is silent - stale line numbers don't break anything, they just mislead readers. The pattern is cross-cutting (affects all documentation) and was observed 5 times in this PR alone.

### 2. Incomplete Systematic Renames

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before performing a systematic rename affecting 50+ files

**Warning:** "Use systematic rename checklist covering: class names, function names, module names, variable names, docstrings, documentation file names, documentation cross-references, tripwire messages, test names, command files. Distinguish user-facing terminology (should rename) from internal implementation details (may preserve)."

**Target doc:** `docs/learned/refactoring/systematic-rename-checklist.md`

This is tripwire-worthy because partial renames result in confusing but functional code - the docstring says one thing, the function does another. Multiple instances were caught: test docstrings, tripwire messages, and section headings.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Audit Bot Violations

**Score:** 3/10 (Cross-cutting +2, External tool quirk +1)

**Notes:** Only scores 3 because violations are caught by the audit bot, so they are not truly silent failures. May become tripwire if we document "how to avoid violations before CI runs" - the proactive avoidance is more valuable than the reactive fix.

## Implementation Notes

This learn plan focuses on meta-lessons from the refactoring process rather than documenting the refactoring itself. The 4 documentation items capture:

1. How to write documentation that survives code changes (source pointers)
2. How to execute systematic renames comprehensively (checklist)
3. How to interpret and prevent audit bot violations (patterns)
4. How to maintain accuracy when detection mechanisms evolve (backend detection)

These are cross-cutting concerns that will improve future refactorings and reduce audit bot iterations.
