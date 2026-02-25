---
title: Systematic Rename Checklist
read_when:
  - "planning a multi-file rename across the codebase"
  - "renaming a class or concept that touches many files"
  - "ensuring complete coverage during a rename operation"
tripwires:
  - action: "completing a rename without checking serialization names"
    warning: "Serialization names (JSON keys, provider names, YAML values) may need to be preserved for backward compatibility even when code identifiers change. Check all serialization points."
    score: 6
---

# Systematic Rename Checklist

A comprehensive checklist for renaming a class, concept, or identifier across many files. This complements [systematic-terminology-renames.md](systematic-terminology-renames.md) (which covers LibCST patterns) with a broader coverage checklist.

## Pre-Rename Assessment

Before starting, identify all dimensions of the rename:

- [ ] **Python identifiers** — class names, function names, variable names, type annotations
- [ ] **String literals** — dict keys, JSON fields, YAML values, CLI output
- [ ] **Documentation** — docs/learned/, CLAUDE.md, AGENTS.md, docstrings
- [ ] **Commands** — CLI command names, slash commands in `.claude/`
- [ ] **Tests** — assertion strings, fixture names, fake class names
- [ ] **Serialization** — stored values that existing data depends on

## Phase-by-Phase Execution

### Phase 1: Code Identifiers

Use `libcst-refactor` agent for Python identifier renames. After LibCST:

- [ ] Grep entire repo for old identifier name
- [ ] Check string literals LibCST missed (dict keys, JSON fields)

### Phase 2: Documentation and Commands

- [ ] Update docs/learned/ files referencing old name
- [ ] Update CLAUDE.md/AGENTS.md if referenced
- [ ] Update `.claude/` artifacts (commands, skills) if referenced
- [ ] Update source pointer HTML comments

### Phase 3: Tests

- [ ] Update test class names and file names
- [ ] Update assertion strings containing old name
- [ ] Update fake/mock class names
- [ ] Update fixture data

### Phase 4: Serialization Compatibility

Decide per serialization point: **rename or preserve?**

- [ ] Provider name strings (e.g., `"github-draft-pr"` was preserved when `DraftPRPlanBackend` was renamed to `PlannedPRBackend`)
- [ ] JSON schema field names in stored data
- [ ] YAML metadata values in GitHub issues
- [ ] CLI flag names (breaking change if renamed)

## Real Example: DraftPRPlanBackend to PlannedPRBackend

PR #8038 renamed across 100+ files:

- **Code identifiers**: Renamed via LibCST
- **Serialization preserved**: `"github-draft-pr"` provider name kept for backward compatibility
- **Tests updated**: All fake and test references updated
- **Documentation updated**: All docs/learned/ references updated

## Verification

```bash
# Confirm no remaining old references in code
grep -r "OldClassName" src/ packages/ tests/

# Confirm docs updated
grep -r "OldClassName" docs/learned/

# Run type checker and tests
make ty && make test
```

## Related Documentation

- [Systematic Terminology Renames](systematic-terminology-renames.md) — LibCST patterns and three-phase workflow
- [Command Rename Checklist](../cli/command-rename-checklist.md) — CLI-specific rename steps
