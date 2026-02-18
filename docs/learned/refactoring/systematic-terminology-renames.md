---
title: Systematic Terminology Renames
read_when:
  - "renaming a concept across the codebase (e.g., step→node)"
  - "planning a multi-phase identifier rename"
  - "using LibCST for batch symbol renames"
tripwires:
  - action: "completing a terminology rename without grepping for string literals"
    warning: "LibCST leave_Name visitor does NOT rename string literals used as dict keys. After LibCST batch rename, grep for old identifier as string key."
  - action: "renaming display strings without checking test assertions"
    warning: 'After display-string renames, search test assertions: `grep -r ''"old_term"'' tests/`. Not caught by linters or type checkers.'
---

# Systematic Terminology Renames

Guide for renaming a concept (e.g., "step" → "node") across the entire codebase.

## Three-Phase Workflow

### Phase 1: Display Strings

Rename user-visible strings first — CLI output, help text, documentation, comments.

**Tools**: Edit tool with `replace_all`, targeted grep + manual edits

**Verification**: Run the application and visually confirm output uses new terminology.

### Phase 2: LibCST Identifiers

Use the `libcst-refactor` agent for Python identifier renames — function names, variable names, class names, type annotations.

**Tools**: `libcst-refactor` agent with batch rename operations

**Limitations**:

- `leave_Name` visitor does NOT rename string literals
- Does not rename dict keys that are strings (e.g., `{"step_id": value}`)
- May miss files outside the agent's configured scope

**Post-rename grep**: Always grep the entire codebase for the old symbol name after LibCST completes.

### Phase 3: Dict Key Strings and Remaining References

Manually rename string literals used as dict keys, YAML fields, JSON schema keys, and documentation references.

**Tools**: Grep + targeted Edit tool edits

**Verification**:

1. Run type checker (`ty` or `mypy`) — catches type annotation mismatches
2. Run full test suite — catches runtime mismatches
3. Grep for old term across entire repo — catches documentation and comments

## Scope Boundary Checking

Before starting, define the rename scope:

- **Internal only**: Functions, variables, types within `src/` and `packages/`
- **External-facing**: CLI flags, JSON output fields, YAML schema keys
- **Documentation**: `docs/learned/`, `AGENTS.md`, `CLAUDE.md`
- **Tests**: Assertion strings, fake data, fixture names

External-facing renames require backwards-compatibility consideration (or explicit decision to break).

## Verification Checklist

```bash
# 1. No remaining old-term references in Python
grep -r "old_term" src/ packages/ tests/

# 2. No remaining old-term in documentation
grep -r "old_term" docs/learned/

# 3. Type checker passes
make ty

# 4. Tests pass
make test
```

## Related Documentation

- [LibCST Systematic Import Refactoring](libcst-systematic-imports.md) — LibCST patterns and gotchas
- [Command Rename Checklist](../cli/command-rename-checklist.md) — CLI-specific rename steps
