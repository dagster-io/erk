---
title: Roadmap Marker Testing Patterns
read_when:
  - "writing tests for HTML comment marker wrapping or extraction"
  - "adding test coverage for roadmap table manipulation"
  - "understanding the test coverage model for marker-bounded content"
last_audited: "2026-02-15 17:17 PT"
---

# Roadmap Marker Testing

## Test Coverage Categories

### Marker Wrapping (`wrap_roadmap_tables_with_markers`)

- Adds markers around phase sections
- Handles content with no phases (no-op)
- Replaces existing markers (idempotency)
- Wraps single phase correctly
- Wraps multiple phases correctly

### Marker Extraction (`extract_roadmap_table_section`)

- Returns section content between markers
- Returns None when markers absent
- Handles incomplete markers (only start, only end)
- Returns correct offsets for replacement

## Test Data Approach

Use inline markdown strings with phase headers and tables. Keep test data self-contained in each test function rather than sharing fixtures — each test should be understandable in isolation.

## Assertion Patterns

- Check marker presence in output (`ROADMAP_TABLE_MARKER_START in result`)
- Verify section content matches expected
- Validate start/end offsets enable correct replacement (round-trip: extract → modify → replace)

## Test Location

<!-- Source: packages/erk-shared/tests/unit/github/metadata/test_roadmap_markers.py -->

Tests live in `packages/erk-shared/tests/unit/github/metadata/` alongside other roadmap tests, following the erk_shared test directory convention.

## Related

- [roadmap-table-markers.md](../architecture/roadmap-table-markers.md) — Architecture of the marker system
- [test-coverage-review-standards.md](test-coverage-review-standards.md) — How this test file exemplifies thorough coverage
