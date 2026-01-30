---
title: Hooks Tripwires
read_when:
  - "working on hooks code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from hooks/*.md frontmatter -->

# Hooks Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding new coding standards reminders** → Read [Reminder Consolidation Pattern](reminder-consolidation.md) first. Check if reminder is already injected via PreToolUse hook before adding to UserPromptSubmit. Duplicate reminders increase noise and waste tokens. Read reminder-consolidation.md first.

**CRITICAL: Before creating a PreToolUse hook** → Read [PreToolUse Hook Implementation Guide](pretooluse-implementation.md) first. Test against edge cases. Untested hooks fail silently (exit 0, no output). Read docs/learned/testing/hook-testing.md first.
