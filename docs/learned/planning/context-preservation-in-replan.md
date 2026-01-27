---
title: Context Preservation in Replan Workflow
read_when:
  - "implementing replan workflow"
  - "creating consolidated plans"
  - "understanding sparse plan prevention"
tripwires:
  - action: "entering Plan Mode in replan or consolidation workflow"
    warning: "Gather investigation context FIRST (Step 6a). Enter plan mode only after collecting file paths, evidence, and discoveries. Sparse plans are destructive to downstream implementation."
---

# Context Preservation in Replan Workflow

Critical pattern for preventing sparse plans in replan and consolidation workflows.

## Table of Contents

- [Problem: Sparse Plans](#problem-sparse-plans)
- [Solution: Steps 6a-6b](#solution-steps-6a-6b)
- [Step 6a: Gather Investigation Context](#step-6a-gather-investigation-context)
- [Step 6b: Enter Plan Mode with Full Context](#step-6b-enter-plan-mode-with-full-context)
- [Why This Matters](#why-this-matters)
- [Implementation Reference](#implementation-reference)

---

## Problem: Sparse Plans

### What Are Sparse Plans?

Sparse plans contain generic placeholders instead of specific implementation details:

- **Generic file references** instead of specific paths
- **Missing evidence** (no line numbers, commit hashes, or citations)
- **Vague verification criteria** (no testable success criteria)

### Example of a Sparse Plan

```markdown
## Implementation Steps

1. Update gateway documentation
2. Add missing tripwires
3. Fix import statements
```

**Problems:**

- Which gateway documentation file?
- Which tripwires are missing? Where should they go?
- Which import statements? In which files?

### Why Sparse Plans Fail

When an implementing agent receives a sparse plan:

1. **Must re-discover everything** - All investigation work is repeated
2. **May make different choices** - Without evidence, agent guesses
3. **Cannot verify completion** - No clear success criteria
4. **Wastes expensive context** - Investigation findings were already gathered

### Root Cause

Sparse plans occur when agents enter Plan Mode **before** gathering investigation context from Steps 4-5. The investigation findings exist in the conversation history, but they're not explicitly collected and structured before plan creation.

---

## Solution: Steps 6a-6b

The replan workflow was enhanced with two explicit steps before plan creation:

### Step 6a: Gather Investigation Context

**Before entering Plan Mode**, collect and structure all investigation findings.

### Step 6b: Enter Plan Mode with Full Context

**After gathering context**, use EnterPlanMode with explicit requirements for incorporating findings.

This creates a **checkpoint** that ensures investigation context is preserved in the final plan.

---

## Step 6a: Gather Investigation Context

### What to Collect

Before entering Plan Mode, gather:

#### 1. Investigation Status per Plan

For each original plan being replanned:

- **Completion percentage**: "4/11 items implemented"
- **Status breakdown**: How many items are done, partial, not started

#### 2. Specific Discoveries

Concrete evidence from codebase exploration:

- **File paths**: `docs/learned/architecture/gateway-inventory.md`
- **Line numbers**: `gateway-inventory.md:45` for specific changes
- **Commit hashes**: `a1b2c3d` that implemented the feature
- **PR numbers**: #5432 that added the functionality

#### 3. Corrections Found

What the original plan(s) got wrong:

- **Non-existent files**: Plan referenced `foo.md`, but it doesn't exist
- **Wrong file names**: Plan said `bar.md`, but it's actually `baz.md`
- **Outdated APIs**: Plan used old function signature
- **Already completed**: Item was implemented in PR #5432

#### 4. Codebase Evidence

Actual implementation details discovered:

- **Function names**: `sanitize_worktree_name()`, not guessed `sanitize_name()`
- **Class signatures**: `class CommandExecutor(ABC, WorkspaceContext)`
- **Config values**: `max_length=31`, `timestamp_format="%m-%d-%H%M"`
- **Data structures**: Fields in dataclasses, type annotations

### For Consolidation Mode

Additionally gather:

- **Overlap analysis**: Which items appeared in multiple source plans
- **Merge decisions**: Why items were combined or kept separate
- **Attribution map**: Which source plan contributed each item

### Example Context Gathering

```markdown
## Investigation Context Collected

### Plan #6134 Status

- **4/11 items implemented** (36%)
- Implemented: Items 1, 3, 7, 9
- Partially complete: Items 2, 5 (files exist but need updates)
- Not started: Items 4, 6, 8, 10, 11

### Specific Discoveries

- `docs/learned/architecture/prompt-executor-gateway.md:67` - Still references Haiku model (needs update to Sonnet)
- `docs/learned/sessions/preprocessing.md` - File exists (81 lines), needs UPDATE not CREATE
- Pattern template files - Confirmed DO NOT exist anywhere in docs/learned/

### Corrections to Original Plan

- **#6134 Item 3**: Said to CREATE `preprocessing.md`, but file exists since PR #5789
- **#6131 Item 5**: Referenced `docs/patterns/`, but correct path is `docs/learned/patterns/`
- **#6130**: Assumed helper function `parse_session()`, actual name is `parse_session_file_path()`

### Codebase Evidence

- Session preprocessing: `src/erk/claude/session_preprocessor.py:142-168`
- Token limit constant: `SINGLE_FILE_TOKEN_LIMIT = 20_000` at line 23
- Multi-part naming: `{session_id}.part{N}.jsonl` format (line 156)
```

---

## Step 6b: Enter Plan Mode with Full Context

### Critical Requirement

The plan content MUST include investigation findings, not just reference them.

Each implementation step should have:

1. **Specific file paths** - Not "update docs", but "update `docs/learned/foo.md`"
2. **What to change** - Not "update X", but "add entry at line 105 with ABC signature"
3. **Evidence** - Commit hashes, PR numbers, current line numbers proving discovery
4. **Verification criteria** - How to confirm the step is complete

### Anti-Pattern: Sparse Plan Content

```markdown
## Implementation Steps

1. Update session preprocessing documentation
2. Add missing function documentation
3. Fix model references
```

**Problems:**

- Which files? Which functions? Which references?
- No verification criteria

### Correct Pattern: Comprehensive Plan Content

```markdown
## Implementation Steps

### 1. Update Session Preprocessing Documentation

**File:** `docs/learned/sessions/preprocessing.md`

**Changes:**

- Add section on multi-part file handling (reference: `session_preprocessor.py:156`)
- Document 20K token limit constant (line 23)
- Add example of `{session_id}.part{N}.jsonl` naming pattern

**Evidence:** File exists (81 lines), created in PR #5789, last modified 2025-01-10

**Verification:** Document accurately describes `SINGLE_FILE_TOKEN_LIMIT` and multi-part logic

---

### 2. Add parse_session_file_path() Documentation

**File:** `docs/learned/architecture/session-discovery.md`

**Changes:**

- Add entry for `parse_session_file_path()` helper
- Document input format: `{session_id}.jsonl` or `{session_id}.part{N}.jsonl`
- Note return type: `SessionFilePath` dataclass with `session_id` and `part_number` fields

**Evidence:** Function at `src/erk/claude/session_preprocessor.py:78-92`

**Verification:** All session file parsing helpers are documented with signatures

---

### 3. Fix Haiku Model References

**File:** `docs/learned/architecture/prompt-executor-gateway.md`

**Changes:**

- Line 67: Change "Haiku" → "Sonnet"
- Update example from `claude-3-haiku-20240307` → `claude-3-5-sonnet-20241022`

**Evidence:** Model constants at `src/erk/claude/models.py:12-15` show Sonnet as default

**Verification:** No references to Haiku remain in model selection documentation
```

### Key Differences

| Aspect             | Sparse Plan                 | Comprehensive Plan                              |
| ------------------ | --------------------------- | ----------------------------------------------- |
| File reference     | "Update docs"               | "`docs/learned/sessions/preprocessing.md`"      |
| Change detail      | "Add missing info"          | "Add section at line 45 with token limit (20K)" |
| Evidence           | None                        | "PR #5789, file exists (81 lines)"              |
| Verification       | "Documentation is complete" | "SINGLE_FILE_TOKEN_LIMIT is documented"         |
| Executability      | Requires investigation      | Implementable without additional discovery      |
| Function names     | Guessed or generic          | Actual: `parse_session_file_path()` with proof  |
| Source attribution | Not tracked                 | "(from #6134)" or "(from #6131, #6130)"         |
| Line numbers       | Absent                      | "Line 67: change X → Y"                         |

---

## Why This Matters

### Without Context Preservation

1. **Investigation findings lost** - Steps 4-5 discoveries never make it into the plan
2. **Implementing agent repeats work** - Must re-discover everything
3. **Different choices made** - Without evidence, agent makes different assumptions
4. **Verification impossible** - No clear success criteria

### With Context Preservation

1. **Investigation findings preserved** - All discoveries explicitly included
2. **Implementing agent executes directly** - No re-discovery needed
3. **Consistent choices** - Evidence guides decisions
4. **Verification clear** - Testable success criteria provided

### Downstream Impact

A comprehensive plan:

- **Saves expensive context** - Implementing agent doesn't burn tokens re-investigating
- **Reduces errors** - Evidence prevents wrong file names, wrong function signatures
- **Enables verification** - Clear criteria for "done"
- **Preserves decisions** - Why items were merged, what was corrected

---

## Implementation Reference

### Canonical Implementation

The canonical implementation of Steps 6a-6b is in `.claude/commands/erk/replan.md`:

- **Step 6a**: Lines 209-223 (Gather Investigation Context)
- **Step 6b**: Lines 225-250 (Enter Plan Mode with Full Context)

### Learn Plan Specific

For documentation-focused replanning (erk-learn plans), see `.claude/commands/local/replan-learn-plans.md` which reinforces this pattern with documentation-specific context gathering.

### Tripwire

The tripwire for this pattern is:

**Action:** Entering Plan Mode in replan or consolidation workflow

**Warning:** Gather investigation context FIRST (Step 6a). Enter plan mode only after collecting file paths, evidence, and discoveries. Sparse plans are destructive to downstream implementation.

**Severity:** HIGH (affects all consolidation workflows, causes expensive context waste)

---

## Related Documentation

- [Context Preservation Patterns](context-preservation-patterns.md) - Anti-patterns vs. correct patterns with examples
- [Context Preservation Prompting](context-preservation-prompting.md) - Prompt structures for eliciting context
- [Investigation Findings Checklist](../checklists/investigation-findings.md) - Pre-plan-mode verification checklist
- [Replan Command](../../../.claude/commands/erk/replan.md) - Full replan workflow with Steps 6a-6b
