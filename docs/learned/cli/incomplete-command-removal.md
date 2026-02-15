---
title: Incomplete Command Removal Pattern
read_when:
  - "removing a workflow command or CLI entry"
  - "deprecating or deleting a command from erk"
  - "cleaning up dead references after removing a feature"
tripwires:
  - action: "removing a workflow command or CLI entry"
    warning: "Read incomplete-command-removal.md first. Search all string references before removing. String-based dispatch maps like WORKFLOW_COMMAND_MAP aren't caught by type checkers."
---

# Incomplete Command Removal Pattern

When removing a workflow or command, all traces must be removed simultaneously. String-based dispatch maps and configuration references are invisible to type checkers.

## The Problem

Static analysis (ty, mypy, ruff) cannot catch dead references in:

- `WORKFLOW_COMMAND_MAP` string-keyed dictionaries
- Workflow YAML filenames
- CLI help text and documentation
- Slash command files referencing the command
- Test fixtures and test data

## Real Example: objective-reconcile (PR #6882)

The `objective-reconcile` command was removed. Traces that needed cleanup:

1. `WORKFLOW_COMMAND_MAP` entry in `constants.py`
2. Trigger function in the CLI module
3. CLI command registration
4. GitHub Actions workflow YAML file
5. Test fixtures referencing the command

## 4-Step Prevention Pattern

Before removing any command or workflow:

1. **Search string references**: `grep -r "command-name" src/ tests/ .github/ .claude/`
2. **Search WORKFLOW_COMMAND_MAP**: Check `src/erk/cli/constants.py` for the command key
3. **Search workflow files**: Check `.github/workflows/` for matching YAML
4. **Search documentation**: Check `docs/learned/` and `.claude/commands/` for references

## Related Documentation

- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) — 5-place pattern (similar multi-location removal concern)
- [Workflow Commands](workflow-commands.md) — WORKFLOW_COMMAND_MAP structure
