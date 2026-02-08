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

**CRITICAL: Before apply the minimal-set principle** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. ALWAYS apply the minimal-set principle — only allow tools the command actually needs

**CRITICAL: Before claude_session_id is not an environment variable** → Read [Session ID Substitution](session-id-substitution.md) first. CLAUDE_SESSION_ID is NOT an environment variable — it is a string substitution performed by Claude Code's skill/command loader. Treating it as an env var in hooks or Python code will silently produce an empty string.

**CRITICAL: Before commands and agents use different allowed-tools syntax** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. Commands and agents use DIFFERENT allowed-tools syntax — check the format section

**CRITICAL: Before critical: before modifying collateral finding** → Read [Audit-Doc Design Decisions](audit-doc.md) first. CRITICAL: Before modifying collateral finding categories or auto-apply behavior in audit-doc

**CRITICAL: Before omit task from allowed-tools** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. NEVER omit Task from allowed-tools if the command delegates to subagents

**CRITICAL: Before renaming any file in .claude/commands/ or .claude/skills/** → Read [Command Rename Pattern](command-rename-pattern.md) first. Read this doc — renames require a full reference sweep, not just a file move
