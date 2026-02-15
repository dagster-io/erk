# Audit Plan: docs/learned/planning/plan-backend-methods.md

## Context

The user requested an audit of `docs/learned/planning/plan-backend-methods.md` to verify its accuracy against the codebase and learned docs standards. This document describes the PlanBackend ABC and its methods, including implementation details from GitHubPlanStore and FakeLinearPlanBackend.

## Standards Applied

This audit checked against the full learned docs standards from:
- `.claude/skills/learned-docs/learned-docs-core.md` - Content quality standards
- `docs/learned/documentation/audit-methodology.md` - Audit classification system
- `docs/learned/documentation/source-pointers.md` - Source pointer format requirements
- `docs/learned/documentation/stale-code-blocks-are-silent-bugs.md` - The One Code Rule

**Key criteria evaluated:**
1. ✅ The One Code Rule - No verbatim source code (document has none)
2. ❌ Source pointer format - Name-based vs line-range (VIOLATION: uses line ranges)
3. ⚠️ Explain WHY not WHAT - Mixed (some sections good, others need work)
4. ✅ Cross-cutting insight - Connects multiple files effectively
5. ✅ No phantom types - All type references verified
6. ⚠️ DUPLICATIVE vs HIGH VALUE - Method tables need review
7. ❌ Factual accuracy - 3 errors found (schema version, missing method, missing deprecation)

## Audit Findings

### ✅ Accurate Content

The following content is verified as accurate:

1. **Line number references** - All 4 line number citations are correct:
   - `get_metadata_field()`: github.py:198-223 ✅
   - `update_metadata()`: github.py:373-426 ✅
   - `update_plan_content()`: github.py:428-470 ✅
   - `post_event()`: github.py:495-516 ✅

2. **Method behavior descriptions** - All accurate:
   - update_metadata() blocklist of 3 immutable fields ✅
   - update_plan_content() two-tier lookup pattern ✅
   - post_event() ordering (comment first, then metadata) ✅
   - FakeLinearPlanBackend frozen dataclass replacement ✅

3. **ABC hierarchy** - Correctly states PlanBackend extends PlanStore ✅

4. **Architecture references** - Correctly links to gateway-vs-backend.md ✅

### ❌ Issues Found

#### Issue 1: Line Number References Violate Source Pointer Standards (Lines 40, 56, 62, 68)

**Violation:** Uses line-range style references that are high drift risk.

**Evidence:**
- Document uses: "github.py:198-223", "github.py:373-426", "github.py:428-470", "github.py:495-516"
- Source-pointers.md states: "Prefer name-based identifiers (ClassName.method) over line numbers. Names survive refactoring; line numbers go stale silently."
- Line numbers shift on ANY code edit, creating silent staleness

**Standard:** Per source-pointers.md, default to name-based pointers.

**Fix:** Replace with name-based source pointers:
- `GitHubPlanStore.get_metadata_field()` instead of "github.py:198-223"
- `GitHubPlanStore.update_metadata()` instead of "github.py:373-426"
- `GitHubPlanStore.update_plan_content()` instead of "github.py:428-470"
- `GitHubPlanStore.post_event()` instead of "github.py:495-516"

#### Issue 2: Method Tables May Be DUPLICATIVE (Lines 30-34, 44-50)

**Classification question:** Are these tables HIGH VALUE or DUPLICATIVE?

**Evidence:**
- Learned-docs-core.md: "Enumerable catalogs (error types, status values, config options) — encode as Literal types, Enums, or typed constants in source code... reference with source pointers, not tables"
- Method catalogs fall under "enumerable catalogs"
- DUPLICATIVE = "Restates what code already communicates (signatures, imports, field lists)"

**However:** Tables add value beyond the ABC:
- Categorize operations (read vs write)
- Note key implementation details ("Blocklist of 3 immutable fields")
- Provide quick reference structure

**Recommendation:** These are borderline CONTEXTUAL (connect multiple locations) rather than purely DUPLICATIVE. Consider adding source pointers to complement the tables rather than replacing them entirely.

#### Issue 3: Some Sections Explain "What" Not "Why" (Lines 37-40, 60-63)

**Standard:** Learned-docs-core.md: "Explain Why, Not What. The 'what' is already in the code. The 'why' is what agents can't derive from reading source."

**Analysis:**
- ✅ Lines 54-57 (update_metadata): Explains WHY blocklist approach
- ✅ Lines 66-68 (post_event): Explains WHY comment-first ordering
- ⚠️ Lines 37-40 (get_metadata_field): Describes WHAT it does ("Reads a single field... Returns None if unset")
- ⚠️ Lines 60-63 (update_plan_content): Describes HOW two-tier lookup works, not WHY it exists

**Fix:** Enhance or remove "Details" sections that only restate method behavior without explaining design rationale.

#### Issue 4: Missing `close_plan()` in Read Operations Table (Lines 30-34)

**Current state:** Table lists 4 read operations but omits `close_plan()`.

**Evidence:**
- `close_plan()` is defined in PlanStore (store.py:63-73)
- PlanBackend.py line 41 acknowledges it: "close_plan: Close a plan"
- PlanBackend.py line 178: "# close_plan is inherited from PlanStore"

**Fix:** Add `close_plan()` to the read operations table.

#### Issue 5: Incorrect Schema Version Reference (Line 18)

**Current:** "Architecture: Schema v2/v3"

**Evidence:** github.py:1-7 says "Schema Version 2" only. No mention of v3 in the codebase.

**Fix:** Change to "Architecture: Schema v2"

#### Issue 6: Ambiguous FakeLinearPlanBackend Purpose (Lines 70-73)

**Current text:** "The fake implementation at `plan_store/fake_linear.py` validates that the ABC contract works across fundamentally different providers."

**Standard:** Gateway-vs-backend.md: "Fake backends exist only to validate the ABC contract works across different providers. To test code that uses a backend, inject fake gateways into the real backend."

**Issue:** Document doesn't explain the testing pattern distinction:
- Fake backends = ABC validation ONLY
- Testing pattern = fake gateways into real backends

**Fix:** Add testing guidance showing correct vs incorrect patterns.

#### Issue 7: PlanStore Deprecation Not Mentioned (Lines 27-40)

**Evidence:** store.py:1-6:
```python
"""DEPRECATED: Use PlanBackend instead. PlanStore is a read-only subset
and is retained only for backward compatibility with existing type annotations.
```

**Current state:** Document describes PlanStore as current design pattern, not deprecated.

**Fix:** Add deprecation notice in the PlanStore section.

## Recommended Actions

### Priority 1: Fix Standards Violations (CRITICAL)

**Issue 1 - Line number references:**
- Replace all 4 line-range citations with name-based source pointers
- Format: `<!-- Source: path/to/file.py, ClassName.method_name -->`
- Per source-pointers.md: names survive refactoring, line numbers go stale silently

### Priority 2: Fix Factual Errors

**Issue 4 - Missing close_plan():**
- Add `close_plan()` to read operations table (line 30-34)

**Issue 5 - Schema version:**
- Change "Schema v2/v3" → "Schema v2" (line 18)

**Issue 7 - PlanStore deprecation:**
- Add deprecation notice to PlanStore section (lines 27-40)

### Priority 3: Improve Content Quality

**Issue 3 - Explain WHY not WHAT:**
- Enhance get_metadata_field() Details (lines 37-40): Add WHY it exists separate from get_plan()
- Enhance update_plan_content() Details (lines 60-63): Add WHY two-tier lookup (not just HOW)
- Or remove these sections if they only restate method behavior

**Issue 6 - Testing pattern clarity:**
- Add testing guidance to FakeLinearPlanBackend section (lines 70-73)
- Show correct pattern (fake gateway + real backend) vs incorrect (fake backend for testing)

### Priority 4: Review for Duplication (CONSIDER)

**Issue 2 - Method tables:**
- Evaluate whether tables at lines 30-34 and 44-50 are CONTEXTUAL or DUPLICATIVE
- If DUPLICATIVE: Replace with source pointers to the ABC
- If CONTEXTUAL: Keep but add source pointer to the ABC as well

**Current assessment:** Borderline CONTEXTUAL because they add categorization and key details beyond what the ABC provides. Recommend keeping tables but adding source pointers.

## Why Didn't `/local:audit-doc` Catch This?

**Root cause: The command's rules ARE sufficient — the agent didn't follow them.**

The audit-doc command (300 lines, 10 phases) already covers all 7 issues found in this audit:

| Issue | How the command already covers it | Why it was missed |
|-------|----------------------------------|-------------------|
| Line-range references | Phase 5: "Documents specific values, paths, or behaviors that will change" → DRIFT RISK | Agent didn't apply DRIFT RISK classification to prose references |
| Method tables | Phase 5 + learned-docs-core: "Enumerable catalogs... reference with source pointers, not tables" | Agent didn't load the learned-docs skill (prerequisite) |
| "Explain why not what" | Phase 5: "Apply the content quality standards from the learned-docs skill's core rules" | Same — skill not loaded, quality rules not applied |
| Missing close_plan() | Phase 4: "When doc describes component responsibilities, verify the component actually does those things" | Agent didn't cross-check read operations table against actual ABC |

**The command's prerequisite says:** "Load the `learned-docs` skill for content quality standards." The agent skipped this and went straight to factual accuracy checking.

### Proposed Fix: Make Skill Loading Mandatory in Phase 1

The real fix is making the learned-docs skill load unavoidable. Currently the Prerequisites section says:

> "Load the `learned-docs` skill for content quality standards."

This is a passive suggestion before Phase 1 that the agent can skip. The fix:

**Changes to `.claude/commands/local/audit-doc.md`:**

1. **Strengthen the Prerequisites section** — change passive "Load the..." to mandatory language
2. **Add explicit file read as first action of Phase 1** — belt and suspenders

**New Prerequisites section:**

```markdown
### Prerequisites

**MANDATORY:** Load the `learned-docs` skill before starting any phase. This skill defines the content quality standards that drive all classification decisions in this audit. Without it, the audit will miss standards violations (source pointer format, One Code Rule, explain-why-not-what, enumerable catalogs).
```

**New Phase 1 opening (insert before existing "Parse `$ARGUMENTS`..." content):**

```markdown
### Phase 1: Resolve and Read Document

**FIRST:** Read `.claude/skills/learned-docs/learned-docs-core.md`. All subsequent phases depend on these rules — specifically:
- The One Code Rule and its four exceptions (Phase 6: Code Block Triage)
- Source pointer format: name-based over line-range (Phase 2, Phase 5)
- "Explain why, not what" (Phase 5: Adversarial Analysis)
- "Enumerable catalogs → source pointers, not tables" (Phase 5)
- DUPLICATIVE vs HIGH VALUE classification criteria (Phase 5)

Then proceed:
```

This provides two layers:
- The skill load (if the agent supports Skill tool) gives full skill context
- The explicit file read (using Read tool, which every agent has) ensures the rules are in context regardless

**Files to modify:**
- `.claude/commands/local/audit-doc.md` — strengthen Prerequisites + add file read to Phase 1

## Verification

After fixes:
1. Re-read updated document
2. Verify all claims against source files
3. Check that testing guidance aligns with gateway-vs-backend.md
4. Run enhanced `/local:audit-doc` to verify all automated checks pass

## Critical Files

- `packages/erk-shared/src/erk_shared/plan_store/backend.py` - PlanBackend ABC
- `packages/erk-shared/src/erk_shared/plan_store/store.py` - PlanStore ABC (deprecated)
- `packages/erk-shared/src/erk_shared/plan_store/github.py` - GitHub implementation
- `packages/erk-shared/src/erk_shared/plan_store/fake_linear.py` - Fake for ABC validation
- `docs/learned/architecture/gateway-vs-backend.md` - Architecture reference

## Verdict

**SIMPLIFY** - The document provides valuable cross-cutting insight connecting PlanBackend, PlanStore, GitHub implementation, and schema design. However, it violates learned docs standards in several ways:

### Critical Issues (Block Merge)

1. **Line number references violate source pointer standards** - All 4 citations use drift-prone line ranges instead of stable name-based pointers
2. **Missing "why" explanations** - Some Details sections explain WHAT/HOW without explaining WHY the design exists

### Must Fix

3. Schema version error (v2/v3 → v2)
4. Missing close_plan() in read operations table
5. PlanStore deprecation not mentioned
6. Testing pattern guidance incomplete

### Review for Duplication

7. Method tables may be DUPLICATIVE (enumerable catalogs should use source pointers per learned-docs-core.md)

### Assessment

The document has solid technical accuracy (behavioral descriptions are correct) and provides valuable cross-cutting insight. However, the line number references create high drift risk and violate the source pointer standard. The content quality issues (explain why not what) reduce value compared to just reading the ABC source.

**Classification breakdown:**
- ~30% HIGH VALUE (cross-cutting architecture, schema design, WHY explanations)
- ~40% CONTEXTUAL (method categorization, implementation details)
- ~30% DRIFT RISK / DUPLICATIVE (line numbers, WHAT explanations)

After fixes: Would be HIGH VALUE reference material for PlanBackend development.