---
title: Test Coverage Review Standards
read_when:
  - "reviewing test coverage for a PR"
  - "evaluating whether tests are sufficient beyond just file existence"
  - "writing review comments about test coverage"
last_audited: "2026-02-15 17:17 PT"
---

# Test Coverage Review Standards

## Beyond "Test File Exists"

Test coverage review should evaluate depth, not just presence. A test file with one happy-path test provides false confidence.

## Review Checklist

1. **Edge case coverage** — Missing phases, duplicate markers, malformed input, empty collections
2. **Quantitative proportionality** — Are test lines proportional to implementation complexity? A 742-line module with 50 test lines is suspect.
3. **Explicit enumeration** — List test scenarios in review comments so coverage gaps are visible

## Example

PR #7113 marker tests: 1,300+ test lines for a 742-line module. Review enumerated scenarios:

- **Wrapping**: adds markers, handles no phases, replaces existing markers (idempotency), wraps single/multiple phases
- **Extraction**: returns section between markers, returns None without markers, handles incomplete markers (only start, only end)

## What to Look For

- Are error paths tested? (not just happy paths)
- Are boundary conditions covered? (empty input, single item, maximum items)
- Is the test data realistic? (not just `"foo"` and `"bar"`)
- Do tests verify behavior, not implementation? (assert on outputs, not internal state)

## Related

- [testing.md](testing.md) — Erk test reference and patterns
- [roadmap-marker-testing.md](roadmap-marker-testing.md) — Specific example of thorough test coverage
