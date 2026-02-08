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

**CRITICAL: Before ALWAYS apply the minimal-set principle** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. only allow tools the command actually needs

**CRITICAL: Before Commands and agents use DIFFERENT allowed-tools syntax** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. check the format section

**CRITICAL: Before Read this doc — renames require a full reference sweep, not just a file move** → Read [Command Rename Pattern](command-rename-pattern.md) first. Check the relevant documentation.

**CRITICAL: Before treating CLAUDE_SESSION_ID as an environment variable** → Read [Session ID Substitution](session-id-substitution.md) first. CLAUDE_SESSION_ID is NOT an environment variable — it is a string substitution performed by Claude Code's skill/command loader. Treating it as an env var in hooks or Python code will silently produce an empty string.

**CRITICAL: Before using this pattern** → Read [Audit-Doc Design Decisions](audit-doc.md) first. CRITICAL: Before modifying collateral finding categories or auto-apply behavior in audit-doc

**CRITICAL: Before using this pattern** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. NEVER omit Task from allowed-tools if the command delegates to subagents
