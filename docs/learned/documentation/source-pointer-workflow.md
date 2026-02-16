---
description: Pattern for converting code blocks to source pointers in documentation
read_when:
  - converting verbatim code to source pointers
  - reducing code duplication in docs
  - auditing docs with large code blocks
last_audited: "2026-02-16 00:00 PT"
audit_result: new
---

# Source Pointer Conversion Workflow

## Overview

Convert verbatim code blocks to two-part source pointers to prevent documentation staleness.

## The Two-Part Format

1. **HTML comment**: Points to exact location for grep-ability
2. **Prose reference**: Human-readable description of what to find

Example:

```html
<!-- Source: src/erk/capabilities/bundled.py, bundled_skills -->
```

"Add a new entry to the `bundled_skills()` dict, mapping the skill name to its BundledSkillCapability instance."

## Conversion Steps

1. Read `docs/learned/documentation/source-pointers.md` for format details
2. Identify code block to convert
3. Locate the source in codebase
4. Write HTML comment with file path and function/class name
5. Write prose description conveying the same information
6. Remove verbatim code block

## When to Keep Code

Short illustrative snippets (<=5 lines) showing a pattern are acceptable. Replace large blocks (>5 lines) with source pointers. See `docs/learned/documentation/source-pointers.md` for the full exception list (data format examples, third-party API patterns, anti-patterns, CLI invocations).

## Prose Reference Examples

**Dict registration**: "Add a new entry mapping the name to its capability instance"
**Factory call**: "The factory method handles instantiation and registration"
**Config pattern**: "Follow the existing entries in the config dict"
