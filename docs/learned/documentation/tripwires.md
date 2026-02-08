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

**CRITICAL: Before adding a code block longer than a few lines to a learned doc** → Read [Stale Code Blocks Are Silent Bugs](stale-code-blocks-are-silent-bugs.md) first. Check if this falls under the One Code Rule exceptions (data formats, third-party APIs, anti-patterns, I/O examples). If not, use a source pointer.

**CRITICAL: Before adding prettier-ignore to docs/learned/** → Read [Markdown Authoring and Prettier Interactions](markdown-and-prettier.md) first. prettier-ignore is almost never needed in docs. If Prettier is mangling your content, the structure may need rethinking rather than suppression.

**CRITICAL: Before bulk deleting documentation files** → Read [Documentation Audit Methodology](audit-methodology.md) first. After bulk deletions, run 'erk docs sync' to fix broken cross-references.

**CRITICAL: Before classifying constants or defaults in prose as duplicative** → Read [Documentation Audit Methodology](audit-methodology.md) first. Constants and defaults in prose are HIGH VALUE, not DUPLICATIVE. They provide scannability that code alone cannot — an agent shouldn't need to grep to learn a default value.

**CRITICAL: Before continuing to code after discovering scope is larger than expected** → Read [Planless vs Planning Workflow Decision Framework](when-to-switch-pattern.md) first. Stop and switch to planning. Mid-task warning signs (uncertainty accumulating, scope creeping, multiple valid approaches) indicate you should plan. See when-to-switch-pattern.md.

**CRITICAL: Before documenting type definitions without verifying they exist** → Read [Documentation Audit Methodology](audit-methodology.md) first. Type references in docs must match actual codebase types — phantom types are the most common audit finding. Verify with grep before committing.
