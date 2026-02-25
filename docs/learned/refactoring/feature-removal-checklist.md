---
title: Feature Removal Checklist
read_when:
  - "removing a feature from the codebase"
  - "deleting deprecated functionality"
  - "cleaning up after feature removal"
tripwires:
  - action: "removing a feature without checking all artifact categories"
    warning: "Feature removal leaves scattered artifacts. Use this checklist to verify complete removal across source code, tests, constants, documentation, workflows, CLI commands, and glossary entries."
    score: 5
---

# Feature Removal Checklist

Feature removal leaves scattered artifacts that actively mislead agents and break builds. This checklist ensures complete cleanup.

## Case Study: PR #7838

Plan review removal (PR #7838) left behind:

- Broken test file importing deleted functions
- Orphaned schema constants (`REVIEW_PR`, `LAST_REVIEW_PR`)
- 5+ stale documentation files referencing the deleted feature
- Glossary entry for the removed concept

These artifacts caused import errors and misled agents into using deleted APIs.

## Checklist by Category

### 1. Source Code

```bash
grep -r "feature_name\|FeatureName" src/ packages/
```

- Remove functions, classes, and methods
- Remove import statements
- Remove conditional logic gated on the feature

### 2. Tests

```bash
grep -r "feature_name\|FeatureName" tests/ packages/*/tests/
```

- Remove test files for deleted functions
- Remove test helpers that set up deleted feature state
- Fix imports of deleted symbols in remaining test files

### 3. Constants and Schemas

```bash
grep -r "FEATURE_CONSTANT\|feature_field" packages/*/src/
```

- Remove Literal type constants
- Remove from union types (e.g., `PlanHeaderFieldName`)
- Remove from schema validation `optional_fields` sets
- Remove validation blocks for the fields

### 4. Documentation

```bash
grep -r "feature_name\|feature-name" docs/learned/
```

- Delete docs entirely about the removed feature
- Update docs that reference the feature (remove mentions)
- Remove from index files
- Remove from glossary

### 5. Workflows and Actions

```bash
grep -r "feature_name" .github/workflows/ .github/actions/
```

- Remove workflow steps that use the feature
- Remove workflow files dedicated to the feature
- Update workflow conditions that check for the feature

### 6. CLI Commands and Skills

```bash
grep -r "feature_name" .claude/commands/ .claude/skills/
```

- Remove slash commands for the feature
- Update commands that reference the feature
- Remove skill sections about the feature

### 7. Configuration

```bash
grep -r "feature_name" .erk/ pyproject.toml
```

- Remove config entries
- Remove from capability definitions

## Validation

After removal, verify complete cleanup:

```bash
# Should return no results for the deleted feature
grep -r "feature_identifier" src/ packages/ tests/ docs/ .github/ .claude/
```

## Key Insight

Documentation drift during feature removal is a silent failure mode. The code may compile and tests may pass, but stale documentation continues to mislead agents into attempting to use deleted functionality.

## Related Documentation

- [Erk Architecture Patterns](../architecture/erk-architecture.md) — No backwards compatibility principle
