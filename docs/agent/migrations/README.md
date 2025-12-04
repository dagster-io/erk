---
title: Migration Documentation
read_when:
  - "creating temporary migration docs"
  - "understanding migration doc lifecycle"
---

# Migration Documentation

This directory contains **temporary** documentation for active migrations. These docs have a limited lifespan and should be removed once the migration is complete.

## Purpose

Migration docs capture time-sensitive guidance that:

- Helps during an active code transition
- Documents patterns that will become obsolete
- Provides removal criteria for cleanup

## Naming Convention

Files must follow: `YYYY-MM-<topic>.md`

Examples:

- `2024-12-github-gateway-migration.md`
- `2024-12-erkcontext-legacy-compat.md`

## Required Header

Every migration doc MUST include this header block:

```markdown
---
title: [Migration] Topic Name
read_when:
  - "specific trigger conditions"
migration:
  created: YYYY-MM-DD
  remove_when: "description of removal criteria"
  verification: "command to verify migration complete"
---
```

### Header Fields

| Field          | Description                                             |
| -------------- | ------------------------------------------------------- |
| `created`      | Date the migration doc was created                      |
| `remove_when`  | Human-readable description of when to remove            |
| `verification` | Shell command that returns 0 when migration is complete |

## Verification Commands

The `verification` field should contain a grep command (or similar) that:

- Returns **exit code 0** when migration is complete (no matches found)
- Returns **non-zero** when old patterns still exist

Example verifications:

```bash
# Check no old FakeGitHub imports remain
! grep -r "from.*FakeGitHub import" --include="*.py" .

# Check no legacy shims remain
! grep -r "github_issues" --include="*.py" src/
```

## Lifecycle

1. **Create**: When starting a migration, add a dated doc
2. **Reference**: Use during the migration period
3. **Verify**: Run the verification command periodically
4. **Remove**: Delete the doc when verification passes

## Current Migrations

| Document                                                                   | Created    | Status |
| -------------------------------------------------------------------------- | ---------- | ------ |
| [2024-12-github-gateway-migration.md](2024-12-github-gateway-migration.md) | 2024-12-03 | Active |
| [2024-12-erkcontext-legacy-compat.md](2024-12-erkcontext-legacy-compat.md) | 2024-12-03 | Active |
