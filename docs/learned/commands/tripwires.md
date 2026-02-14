---
title: Commands Tripwires
read_when:
  - "working on commands code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from commands/*.md frontmatter -->

# Commands Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding allowed-tools to a command or agent frontmatter** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. ALWAYS apply the minimal-set principle — only allow tools the command actually needs

**CRITICAL: Before adding tool invocations to agent instructions without updating frontmatter** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. allowed-tools frontmatter MUST include every tool the agent's instructions reference. Missing tools cause silent runtime failures.

**CRITICAL: Before creating commands that delegate to subagents** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. NEVER omit Task from allowed-tools if the command delegates to subagents

**CRITICAL: Before creating new agent files in .claude/agents/** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. All agent files MUST have YAML frontmatter with name, description, and allowed-tools. Missing frontmatter causes silent behavioral failures.

**CRITICAL: Before modifying collateral finding categories or auto-apply behavior in audit-doc** → Read [Audit-Doc Design Decisions](audit-doc.md) first. CRITICAL: Read this doc first to understand the conceptual vs mechanical finding distinction

**CRITICAL: Before renaming any file in .claude/commands/ or .claude/skills/** → Read [Command Rename Pattern](command-rename-pattern.md) first. Read this doc — renames require a full reference sweep, not just a file move

**CRITICAL: Before using CLAUDE_SESSION_ID in hooks or Python code** → Read [Session ID Substitution](session-id-substitution.md) first. CLAUDE_SESSION_ID is NOT an environment variable — it is a string substitution performed by Claude Code's skill/command loader. Treating it as an env var in hooks or Python code will silently produce an empty string.

**CRITICAL: Before writing allowed-tools frontmatter** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. Commands and agents use DIFFERENT allowed-tools syntax — check the format section
