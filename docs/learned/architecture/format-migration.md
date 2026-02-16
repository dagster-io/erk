---
title: Format Migration Pattern
read_when:
  - "implementing dual-format support"
  - "modifying parsers or serializers"
  - "adding format migration"
tripwires:
  - action: "implementing format migration"
    warning: "DO preserve input format in update operations. ONLY use new format for newly created objects. DO NOT migrate on every write without explicit user request."
---

# Format Migration: Preserve on Write

## Core Principle

Update operations should preserve input format. Only new objects use new format.

## Three-Part Migration Strategy

1. **Parse both formats** — Graceful fallback, new format first
2. **Generate new format for new objects** — Fresh creation uses modern format
3. **Preserve format for updates** — Legacy stays legacy, new stays new
4. **Validate with flag** — `--allow-legacy` for pre-migration objects

## Detection Pattern (LBYL)

See `parse_roadmap_frontmatter()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`:

```python
# DO: LBYL pre-check
if block_content.strip().startswith("<details>"):
    # Parse new format
else:
    # Parse legacy format

# DON'T: EAFP with try/except
try:
    parse_new_format(content)
except ValueError:
    parse_legacy_format(content)
```

## Remainder Preservation

Legacy formats may have trailing content after structured data. Extract and re-append after serialization.

See `update_step_in_frontmatter()` for the remainder extraction pattern.

## Related Documentation

- [Format Migration Testing](../testing/format-migration-testing.md) — Test patterns for migrations
- [Erk Architecture Patterns](erk-architecture.md) — Core architecture patterns
