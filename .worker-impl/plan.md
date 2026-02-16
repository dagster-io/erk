# Documentation Plan: Enforce YYYY-MM-DD HH:MM PT format for last_audited

## Context

This plan addresses documentation gaps from an implementation that enforced format validation on the `last_audited` frontmatter field in agent docs. The work revealed a contradiction: the schema documentation described `last_audited` as a "free-form date string" while the `/local:audit-doc` command prescribed a specific `YYYY-MM-DD HH:MM PT` format. The implementation resolved this by adding regex validation to enforce the prescribed format, then batch-fixing 122+ existing files that used the incorrect date-only format.

The key insight for future agents is the pattern of using module-level compiled regex for format validation. When adding validation for timestamp or formatted fields, agents should compile the regex at module level (not inline) for both performance and clarity. This cross-cutting pattern applies whenever regex validation is added to validation functions throughout the codebase.

A secondary insight concerns the handling of schema documentation: when implementation behavior diverges from documented behavior (or vice versa), resolving the contradiction through documentation updates is as important as the code change itself. The contradiction between "free-form" in the schema doc and "prescribed format" in the command doc could have caused future confusion if left unaddressed.

## Raw Materials

https://gist.github.com/schrockn/a5637b1b2d9c7f2e2bfd8e9428ddb4a6

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 2     |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Resolve `last_audited` format contradiction

**Location:** `docs/learned/documentation/frontmatter-tripwire-format.md`
**Action:** UPDATE
**Source:** [Impl] + [PR #7115]

**Draft Content:**

```markdown
Update line 39 in the Schema table. Change:

| `last_audited` | No       | string                            | Free-form date string                                                  |

To:

| `last_audited` | No       | string                            | `YYYY-MM-DD HH:MM PT` format (Pacific time, 24-hour clock). Validated by regex in `validate_agent_doc_frontmatter()`. |

This aligns the schema documentation with both:
1. The `/local:audit-doc` command specification (which prescribes this format)
2. The validation logic in operations.py (which enforces it via LAST_AUDITED_PATTERN regex)
```

---

### MEDIUM Priority

#### 1. Validation patterns with module-level regex

**Location:** `docs/learned/architecture/validation-patterns.md` (new)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Validation Patterns
read_when:
  - adding format validation to frontmatter fields
  - implementing regex-based validation
  - working with validate_agent_doc_frontmatter or similar validators
tripwires:
  - action: "adding regex validation inline in a validation function"
    warning: "Compile regex patterns at module level as named constants (e.g., PATTERN_NAME = re.compile(r'...')). This improves performance by compiling once and improves clarity by naming the pattern."
---

# Validation Patterns

## Module-Level Regex Compilation

When adding format validation using regular expressions, compile the pattern at module level as a named constant rather than inline in the validation function.

**Why this matters:**
- Performance: Pattern is compiled once at module load, not on every validation call
- Clarity: Named constant documents the expected format (e.g., `LAST_AUDITED_PATTERN`)
- Reusability: Pattern can be referenced from multiple locations if needed

**Example location:** See `LAST_AUDITED_PATTERN` in `src/erk/agent_docs/operations.py` for the canonical implementation.

## Format Validation Error Messages

When rejecting invalid formats, include both the expected format AND the actual value received in the error message. This makes debugging significantly easier.

**Pattern:** `f"Field '{field}' must match format {EXPECTED}, got: {actual}"`

This allows users (or CI output) to immediately see both what was expected and what was provided, rather than having to grep through files to find the offending value.
```

---

## Contradiction Resolutions

### 1. Free-form vs. Format-enforced `last_audited` field

**Existing doc:** `docs/learned/documentation/frontmatter-tripwire-format.md` line 39
**Conflict:** Schema doc states "Free-form date string" for `last_audited` field, but `/local:audit-doc` command (in `.claude/commands/local/audit-doc.md`) prescribes specific `YYYY-MM-DD HH:MM PT` format (24-hour, Pacific time). The implementation added regex validation enforcing this format, making the "free-form" description incorrect.
**Resolution:** Update the schema table in frontmatter-tripwire-format.md to specify the required format and reference the validation. This ensures future agents understand that `last_audited` has a specific required format, not arbitrary string content.

## Stale Documentation Cleanup

No stale documentation detected. All referenced files exist and paths are current.

## Prevention Insights

### 1. Schema-Implementation Drift

**What happened:** The `last_audited` field was documented as "free-form" while a command specification and validation logic required a specific format.
**Root cause:** Documentation and implementation evolved separately without reconciliation. The command spec prescribed a format, but the schema doc was never updated to match.
**Prevention:** When adding format constraints to existing fields (via validation code OR command specs), always update the corresponding schema documentation in the same PR.
**Recommendation:** ADD_TO_DOC - Include as guidance in the validation patterns doc.

### 2. Inline Regex Compilation

**What happened:** Not an error in this session (agent correctly used module-level), but a common anti-pattern.
**Root cause:** Agents may default to inline `re.match(r'...', value)` without understanding the performance implication of repeated compilation.
**Prevention:** Tripwire warning when adding regex validation to guide agents toward module-level compilation.
**Recommendation:** TRIPWIRE - Cross-cutting pattern that benefits from automatic warning.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Regex compilation at module level for validation

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** Before adding regex validation inline in a function
**Warning:** Compile the regex pattern at module level as a constant (e.g., `PATTERN_NAME = re.compile(r'...')`) rather than inline in the function. This improves performance by compiling once and improves clarity by naming the pattern.
**Target doc:** `docs/learned/architecture/validation-patterns.md`

This is tripwire-worthy because agents may not immediately recognize that inline regex compilation has performance implications. The pattern applies to any validation function using regex - not just frontmatter validation, but also CLI input validation, config validation, and format checking throughout the codebase. Without this tripwire, agents might repeatedly implement inline patterns, leading to subtle performance degradation in frequently-called validation code.

**Scoring breakdown:**
- Non-obvious (+2): The performance difference between inline `re.match()` and pre-compiled patterns isn't immediately apparent. Requires understanding Python's regex compilation behavior.
- Cross-cutting (+2): Applies to validation code throughout the codebase - frontmatter validation, CLI validation, config parsing, format checking.
- Repeated pattern (+0): Only observed once in this session, though the pattern exists in other areas.
- External tool quirk (+0): Standard Python best practice, not an external tool issue.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Format validation error messages include expected + actual

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Helpful debugging practice but not necessarily tripwire-worthy. Would upgrade to tripwire if future sessions show agents repeatedly writing error messages that say "Invalid format" without showing what was received. Current evidence is a single implementation showing the good pattern, not evidence of agents missing the pattern.

### 2. Update schema docs when adding format validation

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** The contradiction in this session demonstrates the risk, but schema-implementation drift is a general software engineering problem. May warrant tripwire if this category of contradiction recurs. Currently better handled as guidance in the validation patterns doc rather than a dedicated tripwire.

## Critical Note: PR Content Discrepancy

The diff analysis revealed that PR #7115's description does not match its actual content. The PR body describes adding validation code and tests, but the actual diff contains only 122+ bulk documentation file updates (changing `last_audited` from date-only to datetime format).

**Implication:** The validation logic (`LAST_AUDITED_PATTERN` and format checking in `validate_agent_doc_frontmatter()`) was likely implemented in a previous PR (possibly #6625 when `/local:audit-doc` was added), or exists on a different branch. The session analysis describes implementing this code, but the merged PR only shows the bulk file fixes.

**For implementing agent:** When creating the validation patterns doc, verify the actual location of `LAST_AUDITED_PATTERN` by grepping current master. Use accurate source pointers based on what actually exists, not what the PR description claimed.