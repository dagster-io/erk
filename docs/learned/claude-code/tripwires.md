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

**invoking skills with context: fork in commands that run via claude --print in CI** → Read [Context Fork Feature](context-fork-feature.md) first. context: fork does NOT create subagent isolation in --print mode. Skill content loads inline and terminal instructions (e.g., 'Output ONLY JSON') contaminate the parent, causing premature termination. Use explicit Task tool delegation instead.

**reloading skills already loaded in the session** → Read [Skill Composition Patterns](skill-composition-patterns.md) first. Skills persist for entire sessions. Check conversation history before loading.
