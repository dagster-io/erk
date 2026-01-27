---
title: Context Preservation Patterns: Anti-Patterns vs. Correct Patterns
read_when:
  - "writing implementation plans"
  - "creating consolidated plans"
  - "avoiding sparse plan content"
---

# Context Preservation Patterns

Example-driven guidance showing the difference between sparse and comprehensive plan content.

## Table of Contents

- [Core Principle](#core-principle)
- [Pattern 1: File References](#pattern-1-file-references)
- [Pattern 2: Evidence and Citations](#pattern-2-evidence-and-citations)
- [Pattern 3: Verification Criteria](#pattern-3-verification-criteria)
- [Pattern 4: Function and Class Names](#pattern-4-function-and-class-names)
- [Pattern 5: Change Descriptions](#pattern-5-change-descriptions)
- [Real-World Examples](#real-world-examples)

---

## Core Principle

**Plans should be executable without the original investigation.**

An implementing agent should be able to execute the plan without:

- Re-reading the original investigation findings
- Re-discovering file paths or function names
- Re-validating which work is complete
- Guessing what "update X" means

All necessary context must be **explicit in the plan**.

---

## Pattern 1: File References

### ❌ Anti-Pattern: Generic File References

```markdown
1. Update gateway documentation
2. Fix the session preprocessing docs
3. Add tripwire to planning documentation
```

**Problems:**

- Which gateway documentation file?
- Which session preprocessing doc?
- Which planning documentation file?

### ✅ Correct Pattern: Specific Paths

```markdown
1. Update `docs/learned/architecture/gateway-inventory.md`
2. Fix `docs/learned/sessions/preprocessing.md`
3. Add tripwire to `docs/learned/planning/lifecycle.md`
```

**Why better:**

- Implementing agent knows exactly which file to edit
- No ambiguity, no need to search
- Verifiable: file exists or doesn't

---

## Pattern 2: Evidence and Citations

### ❌ Anti-Pattern: Missing Evidence

```markdown
## Implementation Steps

1. Document the token limit for session preprocessing
2. Add documentation for the session parser function
3. Update model references from Haiku to Sonnet
```

**Problems:**

- What is the token limit? (Agent must search code)
- Which parser function? What's its name?
- Which files have Haiku references?

### ✅ Correct Pattern: Evidence with Citations

```markdown
## Implementation Steps

### 1. Document Token Limit for Session Preprocessing

**File:** `docs/learned/sessions/preprocessing.md`

**Evidence:**

- Constant: `SINGLE_FILE_TOKEN_LIMIT = 20_000` at `src/erk/claude/session_preprocessor.py:23`
- Used in: `_should_split_session()` function (line 142)

**Changes:** Add section explaining 20K token limit, when splitting occurs, and multi-part file naming

---

### 2. Add Documentation for parse_session_file_path()

**Function:** `parse_session_file_path()`

**Evidence:**

- Location: `src/erk/claude/session_preprocessor.py:78-92`
- Signature: `def parse_session_file_path(path: Path) -> SessionFilePath`
- Returns: `SessionFilePath` dataclass with `session_id: str` and `part_number: Optional[int]`

**Changes:** Document function in `docs/learned/architecture/session-discovery.md` with full signature and examples

---

### 3. Update Model References from Haiku to Sonnet

**File:** `docs/learned/architecture/prompt-executor-gateway.md`

**Evidence:**

- Line 67: Currently references "claude-3-haiku-20240307"
- Correct model: "claude-3-5-sonnet-20241022" (from `src/erk/claude/models.py:12`)

**Changes:** Replace Haiku references with Sonnet model identifier at line 67
```

**Why better:**

- Agent doesn't need to search for constants
- Actual function names provided (not guessed)
- Line numbers make changes precise
- Evidence proves discoveries are real

---

## Pattern 3: Verification Criteria

### ❌ Anti-Pattern: Vague Verification

```markdown
1. Update documentation
   - **Verification:** Documentation is complete
2. Fix references
   - **Verification:** References are correct
```

**Problems:**

- How do you know documentation is "complete"?
- What does "correct" mean?
- Not testable

### ✅ Correct Pattern: Testable Criteria

```markdown
1. Update `docs/learned/sessions/preprocessing.md`
   - **Verification:** Document includes `SINGLE_FILE_TOKEN_LIMIT` constant with value (20K), explains multi-part file pattern `{id}.part{N}.jsonl`, and references `session_preprocessor.py` implementation
2. Fix model references in `prompt-executor-gateway.md`
   - **Verification:** No occurrences of "haiku" or "claude-3-haiku" remain in file; all model examples use Sonnet identifier
```

**Why better:**

- Agent can verify completion objectively
- Clear success criteria
- Testable with grep or file inspection

---

## Pattern 4: Function and Class Names

### ❌ Anti-Pattern: Guessed Names

```markdown
1. Document the session parsing function
2. Add entry for the command executor class
3. Reference the sanitization helper
```

**Problems:**

- Is it `parse_session()`, `parse_session_file()`, or `parse_session_file_path()`?
- Is it `CommandExecutor`, `Executor`, or `CommandRunner`?
- Which sanitization helper? `sanitize()`, `sanitize_name()`, or `sanitize_worktree_name()`?

### ✅ Correct Pattern: Actual Names with Evidence

```markdown
1. Document `parse_session_file_path()` function
   - **Location:** `src/erk/claude/session_preprocessor.py:78-92`
   - **Signature:** `def parse_session_file_path(path: Path) -> SessionFilePath`
2. Add entry for `CommandExecutor` class
   - **Location:** `src/erk/gateway/abc.py:105-142`
   - **Signature:** `class CommandExecutor(ABC, WorkspaceContext)`
3. Reference `sanitize_worktree_name()` helper
   - **Location:** `src/erk/utils/naming.py:45-67`
   - **Signature:** `def sanitize_worktree_name(title: str, max_length: int = 31) -> str`
```

**Why better:**

- No guessing required
- Agent can verify existence
- Signature provides full context

---

## Pattern 5: Change Descriptions

### ❌ Anti-Pattern: What Without How

```markdown
1. Update gateway inventory
2. Add missing entries
3. Fix import paths
```

**Problems:**

- Update what in gateway inventory?
- Which entries are missing?
- Which import paths? Where?

### ✅ Correct Pattern: Specific Changes

```markdown
1. **Update gateway-inventory.md** (`docs/learned/architecture/gateway-inventory.md`)
   - Add missing entries at end of Gateway List section (after line 105):
     - `CommandExecutor` (ABC at `src/erk/gateway/abc.py:105`)
     - `PlanDataProvider` (ABC at `src/erk/gateway/abc.py:142`)
   - Verification: All gateways in `src/erk/gateway/` have entries in inventory
2. **Fix import paths in gateway-inventory.md**
   - Lines 45, 67, 89: Change `erk.gateways.` → `erk.gateway.`
   - Reason: Package was renamed from `gateways` (plural) to `gateway` (singular) in PR #5432
   - Verification: All import examples use `erk.gateway.*`
```

**Why better:**

- Agent knows exactly what to change
- Line numbers make edits precise
- Reasoning explains why
- Verification criteria are testable

---

## Real-World Examples

### Example 1: Replan Issue #6167

#### Before (Sparse)

```markdown
## Implementation Steps

1. Update replan command to preserve context
2. Add investigation gathering step
3. Update learn-plan-specific workflow
```

#### After (Comprehensive)

```markdown
## Implementation Steps

### 1. Add Step 6a to Replan Command

**File:** `.claude/commands/erk/replan.md`

**Changes:**

- Insert new step after line 208 (before "Step 6: Create New Plan")
- Title: "Step 6a: Gather Investigation Context"
- Content: Collect investigation status, discoveries, corrections, and codebase evidence

**Evidence:** Investigation findings from Steps 4-5 were not being preserved (observed in issue #6139 sparse plan output)

**Verification:** Step 6a exists, lists all 4 context types to gather (status, discoveries, corrections, evidence)

---

### 2. Add Step 6b to Replan Command

**File:** `.claude/commands/erk/replan.md`

**Changes:**

- Insert after new Step 6a (around line 225)
- Title: "Step 6b: Enter Plan Mode with Full Context"
- Content: Requirement for comprehensive plan content with file paths, line numbers, evidence, verification

**Evidence:** Anti-pattern vs. correct pattern examples from PR #6140 show sparse vs. comprehensive differences

**Verification:** Step 6b includes CRITICAL tag, anti-pattern example, correct pattern example, and table comparing sparse vs. comprehensive

---

### 3. Update Learn-Plan Replan Workflow

**File:** `.claude/commands/local/replan-learn-plans.md`

**Changes:**

- Line 178: Add parallel investigation with `run_in_background: true`
- Line 205: Add Step 4e "Wait for All Background Investigations (CRITICAL)"
- Line 230: Reinforce context preservation with reference to `/erk:replan` Steps 6a-6b

**Evidence:** Learn plan workflow lacked explicit background investigation wait, causing race conditions

**Verification:** Command includes Step 4e with TaskOutput blocking pattern, references `/erk:replan` context preservation
```

### Example 2: Session Preprocessing Documentation

#### Before (Sparse)

```markdown
1. Document session preprocessing
2. Add token limit information
3. Explain multi-part files
```

#### After (Comprehensive)

```markdown
### 1. Create Session Preprocessing Documentation

**File:** `docs/learned/sessions/preprocessing.md` (CREATE new file)

**Evidence:**

- Implementation: `src/erk/claude/session_preprocessor.py` (215 lines)
- Token limit: `SINGLE_FILE_TOKEN_LIMIT = 20_000` (line 23)
- Multi-part pattern: `{session_id}.part{N}.jsonl` (line 156)
- Compression ratio: 71-92% observed in production (issue #6101 analysis)

**Content sections:**

1. **Purpose**: Why session preprocessing exists (Claude Code 200K context, need to fit multiple sessions)
2. **Token Limit**: 20K single-file limit, when splitting occurs
3. **Multi-Part Files**: Naming pattern, how parts are numbered (1-indexed)
4. **Compression**: Average ratio (75%), implications for fitting sessions
5. **Implementation Reference**: Link to `session_preprocessor.py` with key functions

**Verification:**

- File exists at path
- Contains all 5 sections
- References `SINGLE_FILE_TOKEN_LIMIT` constant
- Includes multi-part naming example
```

---

## Checklist for Comprehensive Plans

Use this checklist to verify plan content is comprehensive:

### File References

- [ ] All files referenced with full paths (e.g., `docs/learned/foo.md`)
- [ ] No generic "update the docs" or "fix the code"

### Evidence

- [ ] Line numbers provided for specific changes
- [ ] Function/class names are actual names, not guessed
- [ ] Commit hashes or PR numbers cited for completed work
- [ ] Constants referenced with values (e.g., `MAX_LENGTH = 31`)

### Change Descriptions

- [ ] Specific changes described (not just "update X")
- [ ] Reasoning provided for changes
- [ ] Connections to other changes explained

### Verification Criteria

- [ ] Success criteria are testable (can run grep, check file, etc.)
- [ ] Criteria are specific (not "complete" or "correct")
- [ ] Verification references concrete artifacts

### Function Names and Signatures

- [ ] Actual function/class names from codebase
- [ ] Signatures provided (parameters, return types)
- [ ] Locations specified (file and line number)

### Attribution (Consolidation Mode)

- [ ] Items marked with source plan (e.g., "from #123")
- [ ] Overlap explained (why items were merged)
- [ ] Attribution table provided

---

## Related Documentation

- [Context Preservation in Replan](context-preservation-in-replan.md) - Why Steps 6a-6b exist, problem and solution
- [Context Preservation Prompting](context-preservation-prompting.md) - Prompt patterns for eliciting context
- [Investigation Findings Checklist](../checklists/investigation-findings.md) - Pre-plan-mode verification checklist
- [Plan Lifecycle](lifecycle.md) - Full plan workflow with investigation findings section
