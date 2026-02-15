# Plan: Broaden SHOULD_BE_CODE to enforce full cornerstone hierarchy

## Context

The `learned-docs-core.md` cornerstone hierarchy defines 4 knowledge placement levels:
1. Type artifact (Enum/Literal)
2. Code comment
3. Docstring
4. Learned doc (escalation path only)

The learn pipeline's `SHOULD_BE_CODE` classification only catches **level 1** (enumerable catalogs → type artifacts). Levels 2–3 (single-artifact knowledge belonging as code comments or docstrings) pass through undetected. This allowed `plan-backend-methods.md` — a method-by-method API reference for a single ABC — to be created 9 days after the standard was established.

## Changes

### 1. Broaden classification description in `documentation-gap-identifier.md`

**File:** `.claude/agents/learn/documentation-gap-identifier.md`

**Line 106** — Change the SHOULD_BE_CODE table row:
```
| SHOULD_BE_CODE    | Enumerable catalog that should be a code type artifact |
```
→
```
| SHOULD_BE_CODE    | Knowledge that belongs in code (type artifacts, docstrings, or comments) |
```

**Lines 109–113** — Replace the narrow "Code artifact test" with a broader "Cornerstone test" that covers all three code-level placements:

```markdown
**Cornerstone test:** Apply the knowledge placement hierarchy from learned-docs-core.md:

1. **Enumerable catalog** (error types, status values, config keys, option sets) →
   should be a Literal type, Enum, or typed constant. Classify as SHOULD_BE_CODE.
2. **Single-artifact API reference** (method tables, implementation details, or
   signatures for one class/ABC/module) → should be docstrings on that artifact.
   Classify as SHOULD_BE_CODE.
3. **Single-location insight** (behavior of one function or one code block) →
   should be a code comment. Classify as SHOULD_BE_CODE.

If the insight spans multiple files or connects systems, it belongs in docs/learned/.
The test is: "Does this knowledge attach to a single code artifact?" If yes → SHOULD_BE_CODE.
```

### 2. Broaden SHOULD_BE_CODE handling in `plan-synthesizer.md`

**File:** `.claude/agents/learn/plan-synthesizer.md`

**Lines 81–84** — Replace:
```markdown
**For SHOULD_BE_CODE items:** Action is CODE_CHANGE. Draft content describes the
type artifact to create or extend (Literal, Enum, typed constant) and where in
the source code it belongs. Do NOT generate markdown documentation content — this
item becomes a code change, not a doc.
```
→
```markdown
**For SHOULD_BE_CODE items:** Action is CODE_CHANGE. Draft content describes the
code change needed — this could be a type artifact (Literal, Enum, typed constant),
docstrings on a class or method, or inline comments. Specify what to add and where
in the source code it belongs. Do NOT generate markdown documentation content —
this item becomes a code change, not a doc.
```

### 3. Update summary statistics label in `documentation-gap-identifier.md`

**Line 173** — Change:
```
| Code artifact items | N |
```
→
```
| Cornerstone redirects (SHOULD_BE_CODE) | N |
```

## Files Modified

| File | Change |
|------|--------|
| `.claude/agents/learn/documentation-gap-identifier.md` | Broaden SHOULD_BE_CODE classification + test |
| `.claude/agents/learn/plan-synthesizer.md` | Broaden SHOULD_BE_CODE output handling |

## Verification

No automated tests to run — these are agent prompt files. Verify by:
1. Re-read both files after edits to confirm internal consistency
2. Mentally trace `plan-backend-methods.md` through the updated pipeline: it's a single-ABC method table → hits rule 2 of the cornerstone test → classified SHOULD_BE_CODE → plan-synthesizer produces a CODE_CHANGE suggesting docstrings on PlanBackend/PlanStore