---
title: Circular Dependency Resolution
read_when:
  - "moving shared utilities between erk and erk_shared packages"
  - "encountering lazy imports (imports inside functions) in erk_shared code"
  - "deciding whether code belongs in erk or erk_shared"
tripwires:
  - action: "importing from erk package in erk_shared code"
    warning: "STOP. erk_shared NEVER imports from erk. Move shared utilities to erk_shared instead. Verify with: grep -r 'from erk\\.' packages/erk-shared/src/"
last_audited: "2026-02-15 17:17 PT"
---

# Circular Dependency Resolution

## Problem

When `erk_shared` needs to import from `erk`, a circular dependency forms. This historically manifested as lazy imports (imports inside functions) to avoid ImportError at module load time. PR #7113 resolved the roadmap utilities instance of this pattern.

## The Package Boundary Rule

- `erk_shared` NEVER imports from `erk`
- `erk` CAN import from `erk_shared`

This is a hard constraint. Any violation creates a circular dependency that will eventually cause import failures.

## Decision Framework

Utilities belong in `erk_shared` when:

1. Used by both `erk` and `erk_shared` packages
2. Have no `erk`-specific dependencies (CLI commands, TUI, etc.)
3. Operate on domain objects that `erk_shared` already defines

## Example: Roadmap Utilities Migration

Three scattered modules (`objective_roadmap_shared.py`, `objective_roadmap_frontmatter.py`, and parsing utilities in `erk.cli.commands.exec.scripts`) were consolidated into a single module at `erk_shared.gateway.github.metadata.roadmap`. The move eliminated lazy imports in `plan_issues.py` that existed solely to break the circular dependency.

## Verification

Check for violations with:

```bash
grep -r 'from erk\.' packages/erk-shared/src/
```

Any matches (other than `from erk_shared`) indicate a circular dependency violation.

## Related

- [erk-shared-package.md](erk-shared-package.md) — Package structure overview
- [roadmap-utilities.md](roadmap-utilities.md) — Specific example of this pattern
- [inline-import-exception.md](inline-import-exception.md) — When inline imports ARE acceptable within the same package
