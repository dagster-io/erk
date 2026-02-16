---
title: False Positive Resolution Workflow
read_when:
  - "responding to automated reviewer flags on justified code"
  - "handling PR review bot false positives"
  - "documenting exceptions to coding standards in PR comments"
last_audited: "2026-02-15 17:17 PT"
---

# False Positive Resolution Workflow

## When Automated Reviewers Flag Justified Code

Automated review bots (dignified-python, linters, etc.) may flag code that is intentionally written a certain way. When you've verified the code is correct despite the flag:

1. **Identify the false positive** — Understand why the code is correct despite the flag
2. **Document in PR comment** — Reply to the review thread with "False positive: ..." prefix explaining the justification
3. **Request re-review** — Summary review should include "False Positive Resolution" section if applicable
4. **Resolve thread** — Mark thread resolved after explanation accepted

## Why Prefix Matters

The "False positive: ..." prefix serves two purposes:

- Future reviewers (human or AI) can quickly scan for justified exceptions
- It distinguishes "I know this is wrong but leaving it" from "this is correct despite appearances"

## Example

PR #7113 `core.py:737` inline import was flagged by the dignified-python bot. The response documented the circular dependency justification within the `erk_shared.gateway.github.metadata` package. Thread was resolved with explanation.

See [inline-import-exception.md](../architecture/inline-import-exception.md) for this specific pattern.

## Related

- [inline-import-exception.md](../architecture/inline-import-exception.md) — Specific pattern that commonly triggers false positives
