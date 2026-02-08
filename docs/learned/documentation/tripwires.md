---
title: Documentation Tripwires
read_when:
  - "working on documentation code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from documentation/*.md frontmatter -->

# Documentation Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before bulk deleting documentation files** → Read [Documentation Audit Methodology](audit-methodology.md) first. After bulk deletions, run 'erk docs sync' to fix broken cross-references.

**CRITICAL: Before creating broad exclusion rules in learned-docs classification** → Read [Documentation Audit Methodology](audit-methodology.md) first. Broad exclusion rules need explicit exceptions. Constants and defaults in prose are HIGH VALUE context, not DUPLICATIVE. Add exception rules with rationale.

**CRITICAL: Before documenting implementation details that are derivable from code** → Read [Documentation Simplification Patterns](simplification-patterns.md) first. Use source pointers instead of duplication. See simplification-patterns.md for patterns on replacing static docs with dynamic references.

**CRITICAL: Before documenting type definitions without verifying they exist** → Read [Documentation Audit Methodology](audit-methodology.md) first. Type references in docs must match actual codebase types. Run type verification before committing.
