---
title: Hooks Tripwires
read_when:
  - "working on hooks code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from hooks/*.md frontmatter -->

# Hooks Tripwires

Rules triggered by matching actions in code.

**adding new coding standards reminders** → Read [Reminder Consolidation Pattern](reminder-consolidation.md) first. Grep for the reminder text across AGENTS.md, hooks, and skills first — it may already exist at another tier. Duplicate reminders waste tokens and teach agents to ignore them. Read reminder-consolidation.md first.

**creating a PreToolUse hook** → Read [PreToolUse Hook Design Patterns](pretooluse-implementation.md) first. Broken hooks fail silently (exit 0, no output) — indistinguishable from correct no-fire behavior. Structure as pure functions + thin orchestrator. Read docs/learned/testing/hook-testing.md first.

**reproducing stdin JSON parsing or file detection logic in a new hook** → Read [PreToolUse Hook Design Patterns](pretooluse-implementation.md) first. Reuse the canonical pure functions in pre_tool_use_hook.py. Writing from scratch reintroduces edge cases already solved (empty stdin, missing keys, wrong types).

**writing a system reminder longer than 5 lines** → Read [System Reminder Composition Patterns](replan-context-reminders.md) first. Long reminders get skimmed or ignored. Apply the three-property test: concise (2-3 sentences or 4-5 bullets), specific (exact step/file/action references), verifiable (agent can self-check completion). Read replan-context-reminders.md.
