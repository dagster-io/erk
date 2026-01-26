---
title: Capabilities Tripwires
read_when:
  - "working on capabilities code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from capabilities/*.md frontmatter -->

# Capabilities Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before using `is_reminder_installed()` in hook check** → Read [Adding New Capabilities](adding-new-capabilities.md) first. Capability class MUST be defined in reminders/ folder AND registered in registry.py @cache tuple. Incomplete registration causes silent hook failures.
