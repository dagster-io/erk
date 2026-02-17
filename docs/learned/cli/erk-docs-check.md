---
title: erk docs check Command
read_when:
  - "validating documentation frontmatter and structure"
  - "debugging CI failures in documentation checks"
  - "understanding how erk docs check works"
tripwires:
  - action: "calling is_learned_docs_available() in CLI code"
    warning: "Function signature requires repo_ops and cwd kwargs: is_learned_docs_available(repo_ops=..., cwd=...). Omitting either kwarg will cause a TypeError."
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
---

# erk docs check Command

The `erk docs check` command validates documentation health in `docs/learned/`. It runs two phases of validation and is integrated into CI.

## Two-Phase Operation

### Phase 1: Frontmatter Validation

Validates that all documentation files have correct YAML frontmatter:

- Required fields present (`title`, `read_when`)
- YAML syntax is valid
- Tripwire format is correct (when `tripwires` field exists)

Also validates `tripwires-index.md` structure.

<!-- Source: src/erk/cli/commands/docs/check.py, validate_agent_docs() and validate_tripwires_index() -->

### Phase 2: Sync Check

Verifies that auto-generated files are in sync with source frontmatter by running a dry-run sync and comparing output:

- `docs/learned/index.md` matches current frontmatter
- `docs/learned/<category>/index.md` files are current
- `docs/learned/<category>/tripwires.md` files are current
- `docs/learned/tripwires-index.md` counts are accurate

<!-- Source: src/erk/cli/commands/docs/check.py, sync_agent_docs(dry_run=True) -->

## Usage

```bash
# Run all checks
erk docs check

# Typical CI integration
make fast-ci  # includes erk docs check
```

## Exit Codes

| Code | Meaning                                      |
| ---- | -------------------------------------------- |
| 0    | All checks pass (or no docs directory found) |
| 1    | Validation or sync check failed              |

## Fixing Failures

If Phase 1 fails: fix the frontmatter in the flagged documentation file.

If Phase 2 fails: run `erk docs sync` to regenerate auto-generated files, then commit.

## Relationship to Other Commands

- `erk docs sync` — Regenerates auto-generated files (run when Phase 2 fails)
- `erk docs validate` — Standalone frontmatter validation (Phase 1 only)

## Related Documentation

- [Documentation Standards](../documentation/) — Documentation structure and conventions
