---
title: audit-pr-docs Bot Drift Detection Patterns
read_when:
  - "interpreting audit-pr-docs bot findings"
  - "understanding documentation drift categories"
  - "working with the pr-address workflow"
---

# audit-pr-docs Bot Patterns

The audit-pr-docs bot detects documentation drift during PR review.

## Categories of Drift

Based on PR #7473 (9 findings):

1. **Wrong predicates:** Docs claim `pr_number is not None` but code checks `pr_url is not None`
2. **Missing items:** Command exists in registry but missing from availability table
3. **Stale counts:** "Six commands" but actually seven
4. **Verbatim code drift:** Copied code block references non-existent field

## Addressing Findings

The pr-address workflow automates fixes:

1. Bot posts findings as review comments
2. `/erk:pr-address` reads comments and applies fixes
3. Fixes committed to same PR branch

## Prevention

- Use source pointers instead of verbatim code
- Avoid numeric counts in prose
- Cross-reference implementation when documenting lists
- Run audits before PR submission

## Related Documentation

- [Documentation Specificity Guidelines](../documentation/specificity-guidelines.md) — what belongs in docs vs source
- [ABC Interface Documentation Patterns](../architecture/abc-documentation-patterns.md) — avoiding method count drift
