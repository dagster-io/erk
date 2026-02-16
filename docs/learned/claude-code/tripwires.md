---
title: Claude Code Tripwires
read_when:
  - "working on claude-code code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from claude-code/*.md frontmatter -->

# Claude Code Tripwires

Rules triggered by matching actions in code.

**creating Claude Code agent commands in .claude/commands/** → Read [Claude Code Agent Command Patterns](agent-commands.md) first. Filenames MUST match the command name for discoverability.

**creating a skill or command with context: fork without explicit task instructions** → Read [Context Fork Feature](context-fork-feature.md) first. Skills/commands with context: fork need actionable task prompts. Guidelines-only content returns empty output.

**reading a file over 2000 lines with the Read tool** → Read [Claude Code Tool Limitations](tool-limitations.md) first. Read tool truncates at 2000 lines by default. Use offset/limit parameters to page through large files, or use GitHub API for plan content.

**reloading skills already loaded in the session** → Read [Skill Composition Patterns](skill-composition-patterns.md) first. Skills persist for entire sessions. Check conversation history before loading.
