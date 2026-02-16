---
title: Auto-Generated Reference Documentation
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
read_when:
  - "adding or modifying CLI commands"
  - "changing erk exec command structure"
  - "CI fails with exec reference check error"
tripwires:
  - action: "adding or modifying CLI commands without regenerating reference docs"
    warning: "After CLI changes, run 'erk-dev gen-exec-reference-docs' to update auto-generated exec reference documentation. Stale docs confuse users and agents."
  - action: "exec reference check fails in CI"
    warning: "Run 'erk-dev gen-exec-reference-docs' via devrun agent. This is routine maintenance after exec script changes, not a bug to investigate."
---

# Auto-Generated Reference Documentation

## The Synchronization Problem

Click help text lives in Python source. The `.claude/skills/erk-exec/reference.md` file must mirror this source of truth. Manual synchronization fails because:

1. Agents don't know when CLI structure changes
2. Humans forget to regenerate after small tweaks
3. Stale docs cause confusion (documented flags don't exist, new commands missing)

## The Solution: Introspection-Based Generation

<!-- Source: packages/erk-dev/src/erk_dev/exec_reference/generate.py, collect_exec_commands -->

The `erk-dev gen-exec-reference-docs` command introspects the live Click command tree at runtime. It walks `exec_group.commands`, extracts parameter metadata, and generates markdown tables.

**Why introspection over parsing source:** Click decorators compose at import time. The runtime command tree is the single source of truth — it reflects all decorators, inheritance, and composition patterns.

See `collect_exec_commands()` in `packages/erk-dev/src/erk_dev/exec_reference/generate.py` for the introspection logic.

## Generated Output Structure

The generated reference file includes:

1. **Summary table** — Flat list of all leaf commands (not groups) with one-line descriptions
2. **Detailed sections** — Each command gets usage line, arguments table, options table
3. **Hierarchical organization** — Subcommands nested under their parent groups

The generator flattens command groups in the summary (shows `marker create`, not just `marker`) but preserves hierarchy in detailed sections.

## CI Integration Pattern

<!-- Source: packages/erk-dev/src/erk_dev/commands/gen_exec_reference_docs/command.py, --check flag -->

The `--check` flag enables CI validation:

```bash
erk-dev gen-exec-reference-docs --check
```

Check mode generates content to a temp file, formats it with prettier, then diffs against the committed version. Exit code 1 if they differ.

**Why format before compare:** Prettier normalization ensures the diff catches semantic changes, not whitespace variations.

See `gen_exec_reference_docs_command()` in `packages/erk-dev/src/erk_dev/commands/gen_exec_reference_docs/command.py` for the check logic.

### Makefile Integration

The `fast-ci` and `all-ci` targets include the exec reference check. Failures block CI with a clear remediation message:

```
FAIL: .claude/skills/erk-exec/reference.md is out of date
Run 'erk-dev gen-exec-reference-docs' to regenerate it.
```

This forces regeneration before merge, preventing stale docs from landing.

## When to Regenerate

Run `erk-dev gen-exec-reference-docs` after:

- Adding a new `erk exec` command or group
- Modifying command help text, options, or arguments
- Renaming or removing commands
- Changing command hierarchy (moving commands between groups)

**Anti-pattern:** Committing CLI changes without regenerating docs, then fixing in a follow-up commit. The CI check exists to catch this before push.

## Why This Doc Exists

The cross-cutting insight: **erk uses runtime introspection to keep generated docs in sync with Click source**. This pattern could apply to other generated artifacts (changelog categories, tripwire indices, etc.).

The decision: introspection over parsing. Click's decorator composition model makes source parsing fragile. The runtime command tree is authoritative.

## Related Documentation

- [Exec Command Patterns](exec-command-patterns.md) — Decision framework for where commands live (top-level vs subgroups)
- [Batch Exec Commands](batch-exec-commands.md) — Building batch operations with exec scripts
