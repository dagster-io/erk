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

**Canonical example:** `LAST_AUDITED_PATTERN` in `src/erk/agent_docs/operations.py`

```python
# Module level — correct
LAST_AUDITED_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} PT$")

# Inline — avoid
if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} PT$", value):
```

## Format Validation Error Messages

When rejecting invalid formats, include both the expected format AND the actual value received in the error message. This makes debugging significantly easier.

**Pattern:** `f"Field '{field}' must match format {EXPECTED}, got: {actual}"`

This allows users (or CI output) to immediately see both what was expected and what was provided, rather than having to grep through files to find the offending value.

## Schema-Implementation Consistency

When adding format constraints to existing fields (via validation code or command specs), always update the corresponding schema documentation in the same PR. Without this, schema docs and runtime behavior drift apart, causing confusion for future agents.

**Example:** The `last_audited` field was documented as "free-form date string" while validation enforced `YYYY-MM-DD HH:MM PT`. This contradiction was resolved by updating `docs/learned/documentation/frontmatter-tripwire-format.md` to match the validation.

## Related Topics

- [Frontmatter and Tripwire Format](../documentation/frontmatter-tripwire-format.md) - Schema for agent doc frontmatter
- [Generated Files Architecture](generated-files.md) - How frontmatter drives generated files
