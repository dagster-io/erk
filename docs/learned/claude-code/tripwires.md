---
title: Claude Code Tripwires
read_when:
  - "working on claude-code code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from claude-code/*.md frontmatter -->

# Claude Code Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before PR submission fails with 'Fast mode not available via API'** → Read [Claude Code Agent Command Patterns](agent-commands.md) first. Report to user that manual `/fast` toggle is required. Do not retry automatically. This is a Claude Code API limitation, not an erk bug.

**CRITICAL: Before creating Claude Code agent commands in .claude/commands/** → Read [Claude Code Agent Command Patterns](agent-commands.md) first. Filenames MUST match the command name for discoverability.

**CRITICAL: Before creating a skill or command with context: fork without explicit task instructions** → Read [Context Fork Feature](context-fork-feature.md) first. Skills/commands with context: fork need actionable task prompts. Guidelines-only content returns empty output.

**CRITICAL: Before reloading skills already loaded in the session** → Read [Skill Composition Patterns](skill-composition-patterns.md) first. Skills persist for entire sessions. Check conversation history before loading.
