---
title: GitHub URL Parsing Architecture
read_when:
  - "parsing GitHub URLs"
  - "extracting PR or issue numbers from URLs"
  - "understanding github parsing layers"
last_audited: "2026-02-04 14:11 PT"
audit_result: edited
---

# GitHub URL Parsing Architecture

This document describes the two-layer architecture for parsing GitHub URLs and extracting identifiers (PR numbers, issue numbers, repo names).

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│              CLI Layer                       │
│   erk.cli.github_parsing                     │
│   - Raises SystemExit on failure             │
│   - User-friendly error messages             │
│   - CLI-specific formatting                  │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│            Pure Parsing Layer                │
│   erk_shared.gateway.github.parsing                  │
│   - Returns int | None                       │
│   - No side effects                          │
│   - Reusable across contexts                 │
└─────────────────────────────────────────────┘
```

## Layer 1: Pure Parsing (`erk_shared.gateway.github.parsing`)

See `packages/erk-shared/src/erk_shared/gateway/github/parsing.py:222-265` for `parse_pr_number_from_url` and `parse_issue_number_from_url`.

**Characteristics:**

- Returns `int | None` (never raises)
- No dependencies on CLI frameworks
- Pure functions with no side effects
- Can be used in libraries, tests, scripts

## Layer 2: CLI Wrappers (`erk.cli.github_parsing`)

See `src/erk/cli/github_parsing.py:21-105` for `parse_issue_identifier` and `parse_pr_identifier`.

**Characteristics:**

- Raises `SystemExit` on invalid input
- Provides user-friendly error messages
- Uses click.echo for output formatting
- Only used in CLI command implementations

### Extended Identifier Parsing

**When to use:**

- `parse_issue_identifier`: Plan-related commands where users may use P-prefixed IDs (P123)
- `parse_pr_identifier`: PR-related commands that accept PR numbers or URLs

## Canonical Import Locations

- **Pure parsing**: `erk_shared.gateway.github.parsing` (returns `int | None`)
- **CLI wrappers**: `erk.cli.github_parsing` (returns `int` or exits)

## Usage Guidelines

### In CLI Commands

Use `parse_*_identifier` functions from `erk.cli.github_parsing` (raises SystemExit on invalid input).

### In Libraries and Business Logic

Use pure parsing functions from `erk_shared.gateway.github.parsing` (returns `int | None`).

### In Tests

Use pure functions for predictable testing (no exceptions to catch).

## Anti-Patterns

### Don't: Create Local Helper Functions

Use the shared module `erk_shared.gateway.github.parsing` instead of duplicating regex parsing logic.

### Don't: Re-export from Other Modules

Import directly from the canonical location (no re-exports via `__all__`).

### Don't: Mix Layers

Never use CLI wrappers (which call `SystemExit`) in library code. Use the pure parsing layer.

## Related Topics

- [Subprocess Wrappers](subprocess-wrappers.md) - Similar two-layer pattern for subprocess calls
- [Protocol vs ABC](protocol-vs-abc.md) - Interface design patterns
