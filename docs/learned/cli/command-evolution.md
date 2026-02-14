---
title: Command Evolution and Deletion
read_when:
  - "deleting or replacing a CLI command"
  - "renaming a CLI command"
  - "removing deprecated functionality"
tripwires:
  - action: "deleting a CLI command without checking all reference sites"
    warning: "Follow the deletion checklist: code, tests, docs/learned/, workflow invocations, __init__.py registration, and CLAUDE.md/AGENTS.md references."
---

# Command Evolution and Deletion

Erk follows immediate deletion with no deprecation grace period. When a command is replaced or removed, it is deleted completely in the same PR.

## Deletion Checklist

When deleting a CLI command, verify all reference sites are cleaned up:

1. **Source code**: Delete the command module (e.g., `src/erk/cli/commands/group/my_cmd.py`)
2. **Tests**: Delete associated test files (e.g., `tests/unit/cli/commands/group/test_my_cmd.py`)
3. **Registration**: Remove from `__init__.py` group registration
4. **Documentation**: Delete or update docs in `docs/learned/` that reference the command
5. **Workflow invocations**: Update `.github/workflows/` files that call the command
6. **CLAUDE.md/AGENTS.md**: Remove any references in agent configuration files
7. **Skills/commands**: Update `.claude/` skills or commands that reference the command

## Anti-Pattern: Partial Deletion

Deleting the code but leaving documentation and workflow references is the most common failure mode. Examples from erk's history:

**`erk pr summarize` -> `erk pr rewrite` (PR #6935)**:

- Code was replaced, but `docs/learned/cli/commands/pr-summarize.md` was left behind
- Fixed by deleting the stale doc

**`erk objective reconcile` deletion (PR #6736)**:

- Code was deleted, but two GitHub Actions workflows (`.github/workflows/objective-reconcile.yml` and `objective-reconciler.yml`) still called the deleted command
- Five docs in `docs/learned/` still referenced the deleted command module
- Both workflows were operationally broken until the references were updated

## Why No Deprecation Period

Erk is unreleased, private software with a single team. Deprecation periods exist to give external consumers time to migrate. With no external consumers, deprecation adds complexity without benefit. The cost of a breaking change is one PR, not a migration campaign.

## Related Documentation

- [CLI Development Patterns](../cli/) - Command implementation patterns
