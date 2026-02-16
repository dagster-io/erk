---
title: LBYL Format Detection
read_when:
  - "implementing dual-format parsing"
  - "converting EAFP to LBYL"
  - "adding format detection"
---

# LBYL Format Detection

## Pattern

Use `.strip().startswith()` for format detection before parsing:

```python
# Correct (LBYL)
if block_content.strip().startswith("<details>"):
    parse_details_format(block_content)
else:
    parse_legacy_format(block_content)

# Wrong (EAFP)
try:
    parse_details_format(block_content)
except ValueError:
    parse_legacy_format(block_content)
```

## Why LBYL

- Exceptions are for errors, not control flow
- Pre-check is O(1), exception handling has overhead
- Makes format routing explicit and readable

## Examples

See `parse_roadmap_frontmatter()` and `update_step_in_frontmatter()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`.

## Related Documentation

- [Format Migration Pattern](format-migration.md) — Full migration strategy
- [Erk Architecture Patterns](erk-architecture.md) — Core architecture patterns
