---
title: Objective Duplication Workflow
read_when:
  - "duplicating an objective"
  - "creating objective from template"
---

# Objective Duplication Workflow

## Pattern

1. Fetch existing objective via `gh issue view` or `erk exec get-issue-body`
2. Write content to session plan file
3. Reformat to template structure if needed
4. Validate structure (roadmap table, Test sections)
5. **Critical**: Verify any referenced commands/tools still exist

## Command Verification

Before using commands found in copied objectives:

- Slash commands (`/local:*`) → Check `.claude/commands/`
- CLI commands (`erk *`) → Check `erk --help`

## Related Documentation

- [Command Namespace Distinction](../commands/command-namespace-distinction.md) — Two command types
