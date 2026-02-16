---
title: Inline Import Exception Pattern
read_when:
  - "encountering an inline import flagged by automated reviewers"
  - "deciding whether a circular dependency within the same package justifies an inline import"
  - "responding to PR review bot flags on inline imports"
tripwires:
  - action: "adding an inline import without documenting the circular dependency justification"
    warning: "Inline imports are only acceptable for breaking circular dependencies within the same package. Document the reasoning in a PR comment prefixed with 'False positive: ...' so reviewers understand."
last_audited: "2026-02-15 17:17 PT"
---

# Inline Import Exception Pattern

## When Inline Imports ARE Acceptable

Erk's Python standards prohibit inline imports (imports inside functions). The one exception: breaking circular dependencies within the same package.

## The Pattern

When Module A imports from Module B at module level, and Module B needs to call a function in Module A, Module B must use an inline import to break the cycle.

## Example: erk_shared.gateway.github.metadata

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, line 22 -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py, line 737 -->

In the `metadata` package:

- `roadmap.py` imports `extract_raw_metadata_blocks` from `core.py` at module level
- `core.py` needs `wrap_roadmap_tables_with_markers` from `roadmap.py`
- `core.py` uses an inline import to break the cycle

This is justified because both modules are in the same package and the circular dependency is inherent to their coupled functionality.

## PR Review Bot Handling

Automated review bots (including dignified-python checks) will flag inline imports as violations. When the import is a justified circular dependency break:

1. Reply with "False positive: circular dependency within same package" and explain the cycle
2. Request re-review if needed
3. Resolve the thread after explanation is accepted

See [false-positive-resolution-workflow.md](../reviews/false-positive-resolution-workflow.md) for the general workflow.

## Related

- [circular-dependency-resolution.md](circular-dependency-resolution.md) — Cross-package circular dependency resolution
- [roadmap-table-markers.md](roadmap-table-markers.md) — The specific feature using this pattern
