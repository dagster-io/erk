---
title: "Check 8: Roadmap Block Format"
read_when:
  - "objective check fails on Check 8"
  - "working with legacy objectives"
  - "migrating objective formats"
---

# Check 8: Roadmap Block Format

## What It Validates

Check 8 verifies that roadmap blocks use the modern `<details>` + YAML code block format, not the legacy `---` frontmatter format.

## Backward Compatibility

Use `--allow-legacy` flag to bypass this check for pre-migration objectives:

```bash
erk objective check <issue-number> --allow-legacy
```

## Migration Path

1. New objectives automatically use `<details>` format
2. Existing objectives continue to work (graceful fallback in parser)
3. Updates preserve format (no forced migration)
4. Run `erk objective check` without `--allow-legacy` to identify migration candidates

See `validate_objective()` in `src/erk/cli/commands/objective/check_cmd.py`.

## Related Documentation

- [Validation Patterns](validation-patterns.md) — When to use allow_legacy
- [Roadmap Format Versioning](roadmap-format-versioning.md) — Format migration history
