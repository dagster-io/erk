# Plan: Enhance Audit Commands for Prose-Reality Verification

## Goal

Expand `audit-scan` and `audit-doc` from "find duplicative content" to "verify prose accurately describes systems and concepts."

**Primary focus:** When a document describes how a system works, what a workflow does, or what a component's behavior is - verify those descriptions match the actual codebase. This is about conceptual accuracy, not just mechanical checks like "does this import work."

## Current State

- **audit-scan**: Collects heuristic signals (line count, code blocks, broken paths) but doesn't assess prose content
- **audit-doc**: Has CONTRADICTS category but it's weakly used and depends on manual LLM judgment; framing is "code duplication" not "prose accuracy"

## Key Insight from Exploration

Docs describe systems and concepts at multiple levels:

1. **System behavior descriptions** - "The gateway pattern separates I/O from logic by..."
2. **Workflow explanations** - "When you run `erk prepare`, it first checks X, then does Y..."
3. **Architectural patterns** - "We use discriminated unions for error handling because..."
4. **Component purposes** - "The BranchManager is responsible for..."

These high-level descriptions are the most valuable content to verify - they're what agents rely on to understand the system. Mechanical checks (imports, line numbers) support this but aren't the primary goal.

**Drift risk by description type:**
- **HIGH**: Workflow sequences, component behavior descriptions
- **MEDIUM**: Architectural rationale, pattern explanations
- **LOW**: Conceptual definitions (these change rarely)

---

## Changes to audit-scan.md

### 1. Update Goal Statement

**Current:**
> Score them by audit priority using heuristic signals

**New:**
> Score them by audit priority using heuristic signals, including indicators of prose-reality drift risk

### 2. Add New Signals to Phase 3

Add to the "Per-doc signals to collect" list:

| Signal | Description |
|--------|-------------|
| **behavioral_claims** | Count of statements containing "returns", "raises", "does", "will", "must", "always", "never" in prose (outside code blocks) |
| **step_sequences** | Count of numbered lists with 3+ items (procedural descriptions drift quickly) |
| **line_number_refs** | Count of `:line` or `line X` patterns (need accuracy verification) |
| **symbol_refs** | Count of inline code that looks like function/class names (e.g., backtick-wrapped CamelCase or snake_case identifiers) |

### 3. Update Output Format

Add new fields to the structured output:

```
behavioral_claims: 12
step_sequences: 2
line_number_refs: 5
symbol_refs: 8
```

### 4. Add New Scoring Rules in Phase 4

| Signal | Points | Rationale |
|--------|--------|-----------|
| Has step sequences (step_sequences > 0) | +1 | Procedural descriptions drift quickly |
| High behavioral claim density (behavioral_claims / lines > 0.1) | +2 | Dense claims = more verification needed |
| Has line number references | +1 | Line numbers go stale with refactoring |

### 5. Update Report Stats Section

Add to Phase 6 report:

```markdown
### Stats
- ...existing stats...
- Docs with step sequences: X docs
- Total behavioral claims across all docs: X
```

---

## Changes to audit-doc.md

### 1. Update Goal Statement

**Current:**
> Identify documentation that merely restates what code already communicates.

**New:**
> Identify documentation that: (1) describes systems, workflows, or concepts inaccurately, or (2) merely restates what code already communicates.

Note the priority order: accuracy of system descriptions comes first, duplication second.

### 2. Update Description in Frontmatter

**Current:**
> description: Audit a learned doc for value vs code duplication

**New:**
> description: Audit a learned doc for accuracy and value vs code

### 3. Add New Phase 3.5: System Description Verification

Insert between Phase 3 (Read Referenced Source Code) and Phase 4 (Adversarial Analysis):

```markdown
### Phase 3.5: Verify System Descriptions

**Primary task:** For each section that describes how a system, workflow, or component works, verify the description matches reality.

**System behavior verification:**
- When doc says "X does Y", trace through the actual code to confirm
- When doc describes a workflow sequence, verify the code follows that sequence
- When doc explains why a pattern is used, check the pattern is actually present

**Concept accuracy verification:**
- When doc defines a term (e.g., "a gateway is..."), verify usage in codebase matches
- When doc describes component responsibilities, verify the component actually does those things

**Concrete claim verification (supporting checks):**

**Import claims**: For each `from X import Y` or `import X` in code blocks:
- Attempt verification by checking if the module path exists in the codebase
- Mark as VERIFIED, BROKEN, or CANNOT_VERIFY

**Symbol claims**: For each function/class name mentioned in prose:
- Search source code for definition (`def name` or `class name`)
- Mark as VERIFIED (found), MISSING (not found), or AMBIGUOUS (multiple matches)

**Type claims**: For each "returns X" or "raises X" claim:
- Find the referenced function's signature/implementation
- Check if return type or exception type matches
- Mark as VERIFIED, MISMATCH, or CANNOT_VERIFY

**Line number claims**: For each `file:line` reference:
- Read the file and check if the line contains relevant content
- Mark as ACCURATE (within 5 lines), STALE (off by 6+), or BROKEN (file missing)

Record verification results for use in Phase 4 and Phase 5.
```

### 4. Add New Value Categories to Phase 4

Expand the value categories table:

| Category | Description | Action |
|----------|-------------|--------|
| **STALE** | Was once accurate but code has changed (broken imports, renamed functions, moved files) | Update to match current code |

### 5. Expand CONTRADICTS Guidance

Add to "Specific things to flag as contradictory":

```markdown
**System/Concept Descriptions (highest priority):**
- Descriptions of how a system works that don't match actual implementation
- Workflow explanations where steps are missing, reordered, or no longer exist
- Component behavior descriptions that don't match what the code actually does
- Architectural pattern descriptions that don't reflect current codebase structure
- "When X happens, Y occurs" statements that aren't true in the code

**Mechanical Accuracy (supporting checks):**
- Import paths that don't resolve to actual modules
- Function/class names that don't exist in the codebase
- Return type claims that don't match actual function signatures
- Exception type claims (e.g., "raises RuntimeError") that the function doesn't raise
- Line number references that point to wrong content (off by 6+ lines)
```

### 6. Add Guidance for STALE vs CONTRADICTS

```markdown
**Distinguishing STALE from CONTRADICTS:**

- **CONTRADICTS**: The claim was never true, or states something opposite to code behavior
  - Example: "This function returns a list" when it returns a dict

- **STALE**: The claim was once true but code has evolved
  - Example: Import path changed from `erk.core.foo` to `erk_shared.foo`
  - Example: Function was renamed from `old_name()` to `new_name()`
  - Example: Line number reference points to different code after refactoring

STALE content should be updated; CONTRADICTS content needs deeper review to understand the discrepancy.
```

### 7. Update Phase 5 Output Format

**Current:**
```
Audit: <doc-path> | Verdict: <VERDICT> | Duplicative: X% | High-value: Y% | Contradictions: <count>
```

**New:**
```
Audit: <doc-path> | Verdict: <VERDICT> | Duplicative: X% | Stale: X% | High-value: Y% | Contradictions: <count>
```

Add a verification summary line:
```
Verification: X verified | Y broken/stale
```

### 8. Add New Verdict Option

Add to the verdict options:

- **NEEDS_UPDATE**: Has STALE content that should be corrected but doc is otherwise valuable (distinct from SIMPLIFY which is about removing duplicative content)

### 9. Update Phase 6 Actions

Add new action option:

```markdown
- **"Apply accuracy fixes"** — fix stale imports, update line numbers, correct renamed symbols (only offer if verification found STALE/BROKEN claims but doc is otherwise valuable)
```

Update auto-apply logic:
```markdown
- **NEEDS_UPDATE** verdict → Proceed to Phase 7 with "Apply accuracy fixes + stamp"
```

---

## Files to Modify

1. `.claude/commands/local/audit-scan.md` - Add prose-reality signals and scoring
2. `.claude/commands/local/audit-doc.md` - Add claim verification phase and STALE category

## Verification

After implementation:
1. Run `audit-scan` and confirm new signals appear in output
2. Run `audit-doc` on a doc that describes a system workflow - verify it checks whether the description matches actual code behavior
3. Run `audit-doc` on a doc with known stale content (e.g., outdated line numbers) - verify STALE is detected
4. Confirm the output clearly distinguishes between "description doesn't match reality" (CONTRADICTS) vs "details are outdated" (STALE)