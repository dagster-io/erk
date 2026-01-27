---
title: Investigation Findings Checklist
read_when:
  - "before entering Plan Mode in replan workflow"
  - "verifying context preservation"
  - "creating consolidated plans"
---

# Investigation Findings Checklist

Actionable checklist for verifying investigation context is preserved before plan creation.

## Table of Contents

- [Pre-Plan-Mode Verification](#pre-plan-mode-verification)
- [Plan Content Verification](#plan-content-verification)
- [Post-Plan Review](#post-plan-review)
- [Consolidation-Specific Checks](#consolidation-specific-checks)

---

## Pre-Plan-Mode Verification

Use this checklist before entering Plan Mode (Step 6a completion check).

### Investigation Status

- [ ] **Completion percentage calculated** for each source plan
  - Example: "4/11 items implemented (36%)"
- [ ] **Status breakdown documented**
  - How many items: implemented, partial, not started, obsolete
- [ ] **Work-already-done identified**
  - PR numbers, commit hashes for completed items

### Specific Discoveries

- [ ] **File paths collected** for all relevant files
  - Full paths: `docs/learned/architecture/foo.md`
  - Not generic: "the documentation files"
- [ ] **Line numbers noted** for specific changes
  - Format: `foo.md:45` or `foo.md:45-67` for ranges
- [ ] **Commit hashes recorded** for completed work
  - Format: `a1b2c3d` with description of what was implemented
- [ ] **PR numbers tracked** for features already shipped
  - Format: `#5432` with brief description

### Corrections Found

- [ ] **Non-existent files identified**
  - Original plan said to update `foo.md`, but it doesn't exist
- [ ] **Wrong file names corrected**
  - Original plan said `bar.md`, actual name is `baz.md`
- [ ] **Outdated APIs documented**
  - Original plan used old function signature, actual signature is X
- [ ] **Already-completed items noted**
  - Original plan item was implemented in PR #5432

### Codebase Evidence

- [ ] **Function names verified** (not guessed)
  - Actual: `parse_session_file_path()`, not `parse_session()`
- [ ] **Class signatures documented**
  - Actual: `class CommandExecutor(ABC, WorkspaceContext)`
- [ ] **Config values recorded** with locations
  - Actual: `SINGLE_FILE_TOKEN_LIMIT = 20_000` at line 23
- [ ] **Data structures noted**
  - Dataclass fields, type annotations, default values

---

## Plan Content Verification

Use this checklist after exiting Plan Mode to verify comprehensive plan.

### File References

- [ ] **All files have full paths**
  - Not: "Update documentation"
  - But: "Update `docs/learned/sessions/preprocessing.md`"
- [ ] **No generic references**
  - No "the config file" or "relevant docs"
  - Specific file names always provided

### Change Descriptions

- [ ] **Specific changes described**
  - Not: "Update X"
  - But: "Add entry for CommandExecutor at line 105 with ABC signature"
- [ ] **Line numbers provided** where applicable
  - "Line 67: Change Haiku → Sonnet"
- [ ] **Reasoning included** for changes
  - "Fix import paths (package renamed in PR #5432)"

### Evidence and Citations

- [ ] **Evidence provided** for each step
  - Commit hashes, PR numbers, or file locations
- [ ] **Function names are actual**, not guessed
  - Verified from codebase exploration
- [ ] **Constants cited with values**
  - Not just "the token limit" but "20K token limit"

### Verification Criteria

- [ ] **Success criteria are testable**
  - Can verify with grep, file inspection, or running code
- [ ] **Criteria are specific**, not vague
  - Not: "Documentation is complete"
  - But: "Document includes SINGLE_FILE_TOKEN_LIMIT constant"
- [ ] **Each step has verification**
  - No step lacks a "how to confirm complete" criterion

### No Placeholders

- [ ] **No TODO markers** in plan
  - No "TODO: Add specific file path"
- [ ] **No generic summaries** instead of specifics
  - No "Update as needed" or "Fix where appropriate"
- [ ] **No reference to "findings" without including them**
  - Not: "Based on investigation findings, update X"
  - But: "Update X at line 45 (found to be outdated in investigation)"

---

## Post-Plan Review

After plan is saved to GitHub, perform final review.

### Executability Test

- [ ] **Another agent could execute** without original investigation
  - All necessary context is in the plan
- [ ] **No re-discovery required**
  - File paths, function names, constants are provided
- [ ] **Decisions are documented**
  - Why items were merged, why approach was chosen

### Evidence Preservation

- [ ] **All commit hashes are in plan**
  - Completed work is traceable
- [ ] **All PR numbers are in plan**
  - Shipped features are referenced
- [ ] **All file paths are in plan**
  - Agent knows exactly what to edit

### Verification Criteria Quality

- [ ] **Can verify each step objectively**
  - Success criteria don't require interpretation
- [ ] **Clear "done" definition** for each step
  - Agent knows when to mark step complete

---

## Consolidation-Specific Checks

Additional checks when consolidating multiple plans.

### Overlap Analysis

- [ ] **Overlapping items identified**
  - Which items appeared in multiple source plans
- [ ] **Merge decisions documented**
  - Why items were combined or kept separate
- [ ] **Redundancy eliminated**
  - Duplicate items merged into single step

### Attribution Tracking

- [ ] **Each step marked with source**
  - "(from #123)" or "(from #123, #456)"
- [ ] **Attribution table provided**
  - Clear map of which plan contributed what
- [ ] **Source plan context preserved**
  - Important details from each original plan retained

### Source Plan Analysis

- [ ] **All source plans analyzed** for status
  - Completion percentage for each
- [ ] **Corrections per plan documented**
  - What each original plan got wrong
- [ ] **Work-already-done identified** per plan
  - Which plan items are implemented, by which PR

---

## Example: Good vs. Bad Checklist Results

### ❌ Failed Checklist (Sparse Plan)

```markdown
## Implementation Steps

1. Update session preprocessing documentation
2. Add missing function documentation
3. Fix model references
```

**Checklist failures:**

- ❌ No file paths
- ❌ No line numbers
- ❌ No evidence
- ❌ Vague verification criteria
- ❌ Generic descriptions

### ✅ Passed Checklist (Comprehensive Plan)

```markdown
## Implementation Steps

### 1. Update Session Preprocessing Documentation

**File:** `docs/learned/sessions/preprocessing.md`

**Changes:**

- Add section on multi-part file handling (reference: `session_preprocessor.py:156`)
- Document 20K token limit constant (line 23)
- Add example of `{session_id}.part{N}.jsonl` naming pattern

**Evidence:** File exists (81 lines), created in PR #5789

**Verification:** Document includes SINGLE_FILE_TOKEN_LIMIT constant with value (20K)
```

**Checklist passes:**

- ✅ Full file path provided
- ✅ Specific changes with line numbers
- ✅ Evidence (PR number, file size)
- ✅ Testable verification criteria
- ✅ Concrete implementation details

---

## Quick Reference

### Must-Haves Before Plan Mode

1. Investigation status (completion %)
2. Specific discoveries (files, lines, commits, PRs)
3. Corrections (what original plans got wrong)
4. Codebase evidence (actual names, signatures, values)

### Must-Haves in Plan Content

1. Full file paths (no generic references)
2. Specific changes (with line numbers)
3. Evidence (commit hashes, PR numbers)
4. Testable verification criteria

### Red Flags (Sparse Plan Indicators)

- Generic "update X" without specifics
- No line numbers or file paths
- No evidence or citations
- Vague "complete" verification
- Placeholders or TODOs in plan

---

## Related Documentation

- [Context Preservation in Replan](../planning/context-preservation-in-replan.md) - Why context preservation matters
- [Context Preservation Patterns](../planning/context-preservation-patterns.md) - Examples of sparse vs. comprehensive
- [Context Preservation Prompting](../planning/context-preservation-prompting.md) - Prompt structures for eliciting context
- [Replan Command](../../../.claude/commands/erk/replan.md) - Full workflow with Steps 6a-6b
