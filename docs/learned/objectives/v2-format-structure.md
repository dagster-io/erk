---
title: V2 Objective Format Structure
read_when:
  - "writing tests for v2 objectives"
  - "implementing updates to v2 objective data"
  - "debugging v2 format divergence issues"
tripwires:
  - action: "writing test assertions for v2 objectives"
    warning: "V2 body contains only YAML frontmatter (no markdown tables). Markdown tables live in V2_COMMENT_BODY. Target assertions to the correct location based on format."
---

# V2 Objective Format Structure

V2 objectives store roadmap data in **three distinct locations**, all of which must be kept in sync.

## The Three Stores

| Store            | Location                | Contents                                            |
| ---------------- | ----------------------- | --------------------------------------------------- |
| Frontmatter YAML | Issue body              | Structured metadata including roadmap steps as YAML |
| Body table       | Issue body              | NOT present in v2 - body contains only frontmatter  |
| Comment table    | Separate GitHub comment | Markdown table with step references                 |

## Critical Distinction

**V2 body contains only YAML frontmatter.** The markdown table with step references lives in a separate comment body (`V2_COMMENT_BODY`).

This is different from v1 format where the body contained both frontmatter and the markdown table.

## Test Implications

When writing test assertions for v2 objectives:

- Assertions about YAML data target the body
- Assertions about markdown tables target the comment body
- Do NOT expect `"| - | #777 |"` patterns in the body - those live in comment body

## Update Implications

Functions that update v2 roadmap data must update:

1. Frontmatter YAML in body (via `update_step_in_frontmatter()`)
2. Comment table (via `_replace_table_in_text()`)

Both must implement identical auto-clear/auto-infer semantics. See [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) for the dual-write consistency pattern.

## Source

See `V2_BODY` and `V2_COMMENT_BODY` test fixtures in `tests/unit/cli/commands/exec/scripts/test_update_roadmap_step.py` for canonical examples of the format structure.

## Related Documentation

- [Roadmap Format Versioning](roadmap-format-versioning.md) — Format version differences
- [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) — Write-time vs parse-time semantics
- [Roadmap Validation Architecture](roadmap-validation.md) — Two-level validation
