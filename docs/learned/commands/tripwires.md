---
title: Commands Tripwires
read_when:
  - "working on commands code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from commands/*.md frontmatter -->

# Commands Tripwires

Rules triggered by matching actions in code.

**adding allowed-tools to a command or agent frontmatter** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. ALWAYS apply the minimal-set principle — only allow tools the command actually needs

**committing commands invoked by GitHub Actions workflows without testing in --print mode** → Read [Multi-Phase Command Patterns](multi-phase-command-patterns.md) first. Features that work in interactive mode may fail in --print mode. context: fork is the most notable example — it creates isolation interactively but loads inline in --print mode. Test with `claude --print '/command args'` and verify all phases execute.

**creating commands that delegate to subagents** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. NEVER omit Task from allowed-tools if the command delegates to subagents

**modifying collateral finding categories or auto-apply behavior in audit-doc** → Read [Audit-Doc Design Decisions](audit-doc.md) first. CRITICAL: Read this doc first to understand the conceptual vs mechanical finding distinction

**renaming any file in .claude/commands/ or .claude/skills/** → Read [Command Rename Pattern](command-rename-pattern.md) first. Read this doc — renames require a full reference sweep, not just a file move

**using CLAUDE_SESSION_ID in hooks or Python code** → Read [Session ID Substitution](session-id-substitution.md) first. CLAUDE_SESSION_ID is NOT an environment variable — it is a string substitution performed by Claude Code's skill/command loader. Treating it as an env var in hooks or Python code will silently produce an empty string.

**writing allowed-tools frontmatter** → Read [Tool Restriction Safety Pattern](tool-restriction-safety.md) first. Commands and agents use DIFFERENT allowed-tools syntax — check the format section

**writing multi-phase commands that use subagent isolation** → Read [Multi-Phase Command Patterns](multi-phase-command-patterns.md) first. Multi-phase commands can terminate prematurely if subagent isolation fails in the target execution mode. When a skill invocation or Task call returns empty/early due to isolation failure, the parent context may receive a terminal instruction (e.g., 'Output ONLY JSON') and stop before executing remaining phases. Test with `claude --print` and verify ALL phases execute.
