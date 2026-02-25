---
title: Audit Bot Violation Patterns
read_when:
  - "reviewing audit-pr-docs bot findings"
  - "understanding common documentation violations"
  - "fixing documentation flagged by the audit bot"
---

# Audit Bot Violation Patterns

Common violation patterns found by the `audit-pr-docs` review bot during documentation audits. Understanding these patterns helps write docs that pass review on the first try.

## Pattern 1: Verbatim Code Blocks

**Violation:** Copying source code directly into documentation.

**Why it's flagged:** Copied code silently goes stale when the source changes. The doc looks authoritative even when the code has diverged.

**Fix:** Replace with a source pointer:

```markdown
<!-- Source: src/erk/core/llm_json.py, extract_json_dict -->

See `extract_json_dict()` in `src/erk/core/llm_json.py` for the extraction algorithm.
```

## Pattern 2: Phantom Type References

**Violation:** Documenting types, classes, or enums that don't exist in the codebase.

**Why it's flagged:** Agents try to import phantom types and get cryptic `ModuleNotFoundError` or `ImportError` messages instead of a clear "this doesn't exist."

**Fix:** Verify every type reference with grep before committing. If the type was removed, remove the documentation.

## Pattern 3: Stale Method References

**Violation:** Referencing methods or functions that have been renamed or removed.

**Why it's flagged:** Agents navigate to the referenced location and find nothing, wasting turns investigating.

**Fix:** Use name-based source pointers and verify the target exists. When a method is renamed (e.g., `_build_plan_row` to `_build_row_data`), update all doc references.

## Pattern 4: Line Number Drift

**Violation:** Using line-number references for code that has named symbols.

**Why it's flagged:** Any edit to the file shifts line numbers. The reference becomes incorrect without any visible indication.

**Fix:** Use function/class name anchors instead of line numbers for Python code. See [source-pointer-best-practices.md](source-pointer-best-practices.md).

## Pattern 5: Describing Removed Features

**Violation:** Documenting behaviors, features, or workflows that have been reverted or removed.

**Why it's flagged:** Creates actively harmful documentation — agents confidently follow instructions for features that no longer exist.

**Fix:** Delete the documentation entirely. Documentation of removed features has negative value.

## Related Documentation

- [Source Pointers](source-pointers.md) — Canonical format for code references
- [Audit Methodology](audit-methodology.md) — Full classification framework
- [Source Pointer Best Practices](source-pointer-best-practices.md) — Choosing stable pointer targets
