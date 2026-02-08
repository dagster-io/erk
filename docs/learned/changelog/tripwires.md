---
title: Changelog Tripwires
read_when:
  - "working on changelog code"
tripwires:
  - action: "categorizing internal refactors as Major Changes"
    warning: "NEVER categorize internal refactors as Major Changes—they must be user-visible"
  - action: "exposing implementation details in changelog entries"
    warning: "NEVER expose implementation details in changelog entries"
  - action: "including .claude/commands/local/* changes in changelog"
    warning: "ALWAYS filter .claude/commands/local/* changes (developer-only)"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from changelog/*.md frontmatter -->

# Changelog Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before categorizing internal refactors as Major Changes** → Read [Changelog Categorization Rules](categorization-rules.md) first. NEVER categorize internal refactors as Major Changes—they must be user-visible

**CRITICAL: Before exposing implementation details in changelog entries** → Read [Changelog Categorization Rules](categorization-rules.md) first. NEVER expose implementation details in changelog entries

**CRITICAL: Before including .claude/commands/local/\* changes in changelog** → Read [Changelog Categorization Rules](categorization-rules.md) first. ALWAYS filter .claude/commands/local/\* changes (developer-only)
