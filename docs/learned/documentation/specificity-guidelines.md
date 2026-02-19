---
title: Documentation Specificity Guidelines
read_when:
  - "writing learned documentation"
  - "deciding detail level for docs"
  - "understanding what belongs in docs vs source"
---

# Documentation Specificity Guidelines

## The Tension

PR #7473 revealed tension between:

- **Bot enforcement:** Technical accuracy of every predicate and count
- **Human preference:** High-level guidance without replicating source

Human reviewer dismissed detailed predicate documentation as "overly specific to be in learned docs."

## What Belongs in docs/learned/

- Mental models and patterns
- Decision frameworks
- Tripwires and warnings
- Cross-cutting concerns
- "Why" explanations

## What Should Stay in Source

- Exact method signatures
- Complete field lists
- Verbatim predicate implementations
- Counts that change frequently

## The Source Pointer Solution

When accuracy matters but detail doesn't:

```markdown
Commands are grouped by availability predicate.
See `registry.py` for current predicate implementations.
```

This maintains accuracy without maintenance burden.
