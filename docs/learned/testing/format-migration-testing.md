---
title: Format Migration Testing
read_when:
  - "implementing dual-format support"
  - "writing migration tests"
  - "validating format preservation"
---

# Format Migration Testing

## Required Test Coverage

1. **Parsing tests** — Both formats parse correctly
2. **Rendering tests** — New format renders correctly
3. **Roundtrip tests** — Parse -> update -> parse preserves format
   - `test_render_roundtrip_via_update_legacy()` — Legacy stays legacy
   - `test_render_roundtrip_via_update_details()` — Details stays details
4. **Validation tests** — Check accepts/rejects as expected
5. **Flag tests** — `--allow-legacy` enables backward compatibility

## Naming Convention

Tests covering format variants should be named explicitly:

- `test_*_legacy()` for legacy format
- `test_*_details()` for new format

## Implementation Reference

See tests in `packages/erk-shared/tests/unit/github/metadata/test_roadmap_frontmatter.py`.

## Related Documentation

- [Format Migration Pattern](../architecture/format-migration.md) — Production migration strategy
- [Erk Test Reference](testing.md) — General test patterns
