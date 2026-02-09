---
title: Configuration Tripwires
read_when:
  - "working on configuration code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from configuration/*.md frontmatter -->

# Configuration Tripwires

Rules triggered by matching actions in code.

**adding a new config option without defining it in a Pydantic schema** → Read [Schema-Driven Config System](schema-driven-config.md) first. All config keys must be defined in schema.py with proper ConfigLevel. The schema is the single source of truth — CLI commands discover fields via Pydantic introspection, so manual lists are unnecessary and will diverge.
