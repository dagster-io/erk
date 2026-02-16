---
title: Validation Patterns
read_when:
  - "adding regex validation to a field or input"
  - "implementing input validation with error messages"
  - "understanding module-level regex compilation"
tripwires:
  - action: "adding regex validation inline instead of module-level compilation"
    warning: "Compile regex patterns at module level as named constants. See LAST_AUDITED_PATTERN in operations.py:30 for the canonical example."
last_audited: "2026-02-16 14:15 PT"
audit_result: clean
---

# Validation Patterns

Erk uses module-level compiled regex patterns for input validation. This document captures the pattern and its rationale.

## Module-Level Regex Compilation

All regex patterns used for validation are compiled once at module level as named constants:

```python
# CORRECT: Compile once at module level
LAST_AUDITED_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} PT$")

# WRONG: Compile inside function (repeated compilation)
def validate(value):
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}")  # recompiled every call
```

<!-- Source: src/erk/agent_docs/operations.py:30 -->

### Examples in the Codebase

| File                                                                  | Constant                    | Pattern                      |
| --------------------------------------------------------------------- | --------------------------- | ---------------------------- |
| `src/erk/agent_docs/operations.py:30`                                 | `LAST_AUDITED_PATTERN`      | `YYYY-MM-DD HH:MM PT` format |
| `src/erk/review/parsing.py:21`                                        | `MARKER_PATTERN`            | HTML comment markers         |
| `src/erk/cli/commands/exec/scripts/get_embedded_prompt.py:45`         | `_PLACEHOLDER_PATTERN`      | Template `{{ placeholder }}` |
| `packages/erk-shared/src/erk_shared/naming.py:16`                     | `_SAFE_COMPONENT_RE`        | Safe path component chars    |
| `packages/erk-shared/src/erk_shared/naming.py:25`                     | `_TIMESTAMP_SUFFIX_PATTERN` | Timestamp branch suffixes    |
| `packages/erk-shared/src/erk_shared/gateway/pr/diff_extraction.py:34` | `_DIFF_FILE_PATH_PATTERN`   | Git diff file paths          |

### Naming Convention

- **Public constants**: `UPPER_SNAKE_CASE` (e.g., `LAST_AUDITED_PATTERN`)
- **Private constants**: `_LEADING_UNDERSCORE` (e.g., `_SAFE_COMPONENT_RE`)

## Error Message Pattern

Validation error messages must show both the expected format AND the actual value received:

```python
# CORRECT: Shows both expected and actual
errors.append(
    "Field 'last_audited' must match format"
    f" 'YYYY-MM-DD HH:MM PT', got '{last_audited_data}'"
)

# WRONG: Only shows expected
errors.append("Field 'last_audited' must match format 'YYYY-MM-DD HH:MM PT'")
```

<!-- Source: src/erk/agent_docs/operations.py:218-222 -->

This pattern helps agents debug validation failures without needing to re-read the invalid input.

## Related Documentation

- [Frontmatter and Tripwire Format](../documentation/frontmatter-tripwire-format.md) — Uses LAST_AUDITED_PATTERN for validation
