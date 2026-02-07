---
title: Uncategorized Tripwires
read_when:
  - "working on uncategorized code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from uncategorized/*.md frontmatter -->

# Uncategorized Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding --force flag to a CLI command** → Read [Code Conventions](conventions.md) first. Always include -f as the short form. Pattern: @click.option("-f", "--force", ...)

**CRITICAL: Before adding a function with 5+ parameters** → Read [Code Conventions](conventions.md) first. Load `dignified-python` skill first. Use keyword-only arguments (add `*` after first param). Exception: ABC/Protocol method signatures and Click command callbacks.

**CRITICAL: Before parsing objective roadmap PR column status** → Read [Erk Glossary](glossary.md) first. PR column format is non-standard: empty=pending, #XXXX=done (merged PR), `plan #XXXX`=plan in progress. This is erk-specific, not GitHub convention.

**CRITICAL: Before writing `__all__` to a Python file** → Read [Code Conventions](conventions.md) first. Re-export modules are forbidden. Import directly from where code is defined.
