---
title: Source-of-Truth Maintenance Pattern
read_when:
  - "deciding whether to fix data upstream or enrich downstream"
  - "working with PR body or title updates"
  - "designing data flow between pipeline stages"
tripwires:
  - action: "adding workarounds in downstream consumers to compensate for stale source data"
    warning: "Fix data at the source instead. If PR body is stale after addressing review, update it in pr-address itself rather than enriching objective-update-with-landed-pr."
---

# Source-of-Truth Maintenance Pattern

When data flows through multiple stages (generation -> storage -> consumption), always fix data at the source rather than enriching downstream consumers.

## The Pattern

**Principle**: If data becomes stale at stage N, fix it at stage N, not at stage N+1.

**Anti-pattern**: Adding workarounds in consumers to compensate for stale source data. This creates invisible dependencies and makes the system harder to reason about.

## Concrete Example: PR Body Updates

The PR body is generated during `erk pr submit` and consumed later by `erk land` (via `objective-update-with-landed-pr`).

**Problem**: After `erk pr-address` resolves review comments and makes code changes, the PR body becomes stale. It still describes the original implementation, not the post-review state.

**Wrong approach**: Enrich `objective-update-with-landed-pr` to re-analyze the PR diff and generate a fresh description. This pushes complexity downstream and creates a fragile dependency on diff analysis.

**Correct approach**: Add a Phase 5 to `pr-address` that runs `erk pr update-description` after addressing review comments. This fixes the data at the source, keeping the PR body accurate for all downstream consumers.

This decision was made during the design of PR #6866.

## Decision Criteria

| Situation                                        | Fix Location    | Why                                       |
| ------------------------------------------------ | --------------- | ----------------------------------------- |
| Source data becomes stale after a transformation | At the source   | Keeps all consumers correct automatically |
| Consumer needs data in a different format        | At the consumer | Source format serves other consumers too  |
| Source has no knowledge of the transformation    | At the consumer | Source can't predict consumer needs       |
| Multiple consumers need the same enrichment      | At the source   | Avoids duplicating enrichment logic       |

## Related Documentation

- [PR Submit Workflow Phases](../pr-operations/pr-submit-phases.md) - PR description generation
