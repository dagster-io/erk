---
title: Markdown Parsing Patterns
read_when:
  - "parsing frontmatter from markdown files"
  - "working with agent docs or review definitions"
  - "creating parsing utilities that return structured results"
---

# Markdown Parsing Patterns

This document covers the shared frontmatter parsing infrastructure in `erk.core.frontmatter`, which consolidates frontmatter extraction logic used across multiple modules.

## Overview

Frontmatter parsing is consolidated into a single module to provide:
- **Single source of truth** for all frontmatter operations
- **Consistent error handling** across consumers
- **Type-safe return types** via frozen dataclass
- **Explicit error discrimination** (three distinct failure modes)

## The FrontmatterParseResult Pattern

The `parse_markdown_frontmatter()` function returns a `FrontmatterParseResult` dataclass that encapsulates all parsing outcomes:

```python
@dataclass(frozen=True)
class FrontmatterParseResult:
    metadata: dict[str, object] | None
    body: str
    error: str | None

    @property
    def is_valid(self) -> bool:
        return self.error is None
```

### Field Semantics

- **metadata**: Parsed YAML dict (dict[str, object]), or None if parsing failed
- **body**: Content after frontmatter delimiter. Always populated, even on error, to provide context for error reporting
- **error**: Error message if parsing failed, None on success
- **is_valid**: Convenience property returning True when error is None

### Why body is always populated

Even when parsing fails, the body contains the original content after the frontmatter delimiters. This allows consumers to:
- Provide error context to users
- Fall back to treating entire content as body text
- Log the unparseable content for debugging

## Error Discrimination

The parser distinguishes three distinct failure modes:

| Condition | Error Message | When it occurs |
|-----------|---------------|----------------|
| No frontmatter | "No frontmatter found" | Content doesn't start with `---` delimiter |
| Invalid YAML | "Invalid YAML syntax: {details}" | YAML parser raises exception on malformed syntax |
| Non-dict YAML | "Frontmatter is not a valid YAML mapping" | Parsed YAML is list, scalar, or other non-dict type |

### Pre-check for delimiters

The parser checks for `---` delimiters **before** calling the YAML library. This pre-check distinguishes two scenarios:

- **Content without delimiters** → "No frontmatter found"
- **Empty block** `---\n---\n` → "Frontmatter is not a valid YAML mapping" (empty document parses as None, which is non-dict)

### Common gotcha: Non-dict YAML at top level

YAML frontmatter MUST be a mapping (dict). These are invalid:

```yaml
---
- item1
- item2
---
```

```yaml
---
scalar value
---
```

Both produce the "Frontmatter is not a valid YAML mapping" error because the parsed value is a list or scalar, not a dict.

## Usage Examples

### Basic pattern

```python
from erk.core.frontmatter import parse_markdown_frontmatter

result = parse_markdown_frontmatter(content)

if result.is_valid:
    title = result.metadata.get("title")
    body = result.body
else:
    print(f"Parse error: {result.error}")
```

### Accessing fields

```python
# All fields are always present
metadata = result.metadata  # dict[str, object] | None
body = result.body          # str
error = result.error        # str | None

# is_valid is a convenience property
if result.is_valid:
    # Safe to access metadata (guaranteed non-None)
    pass
```

### Error handling examples

```python
# Pattern 1: Check is_valid (recommended)
if not result.is_valid:
    logger.error(f"Failed to parse {filepath}: {result.error}")
    return None

# Pattern 2: Check error directly
if result.error is not None:
    raise ValueError(f"Parse error: {result.error}")

# Pattern 3: Extract with fallback
metadata = result.metadata or {}
title = metadata.get("title", "Untitled")
```

## Integration Points

This module is used by:

- **`src/erk/agent_docs/operations.py`** — Validates agent documentation files in `docs/learned/`. Parses frontmatter schema: title, read_when, tripwires
- **`src/erk/review/parsing.py`** — Validates review definition files in `.github/reviews/`. Parses frontmatter schema: name, paths, marker, model, etc.

## Design Decisions

### Library over regex

The consolidation chose `python-frontmatter` library over custom regex parsing because:

- **Edge case handling** — Correctly handles multiline strings, special YAML characters, quoted values
- **Well-tested** — Maintained library with established test coverage
- **Ecosystem standard** — Common choice in Python projects
- **Maintenance burden** — Custom regex requires constant updates for new edge cases

The original `agent_docs` module used regex (`^---\s*\n(.*?)\n---` with re.DOTALL), while `review` used the library. Consolidation chose the library approach.

### Frozen dataclass

The result type is a frozen dataclass to:

- **Prevent mutation** — Parsing results are immutable, preventing bugs from accidental modification
- **Type safety** — Named fields prevent typos (vs tuple unpacking)
- **Distribution** — Results can be passed between functions without risk of modification

Previous implementations returned tuples, which are fragile when signature changes (2-tuple vs 3-tuple depending on module).

## Related Topics

- [Generated Files Architecture](generated-files.md) — Frontmatter schema and conventions for agent documentation
- [Erk Architecture Patterns](erk-architecture.md) — Dependency injection and gateway patterns used in parsing
