---
title: ABC Interface Documentation Patterns
read_when:
  - "documenting ABC interfaces"
  - "writing gateway documentation"
  - "avoiding method count drift"
tripwires:
  - action: "listing exact method counts in ABC documentation"
    warning: "Avoid 'N abstract methods' in docs — counts drift as interfaces evolve. Use source pointers instead: 'See PlanDataProvider abstract methods in abc.py'."
---

# ABC Interface Documentation Patterns

PR #7473 review found 3 instances of ABC documentation drift. This doc provides patterns to prevent drift.

## Problem

Manual method lists and counts become stale as interfaces evolve:

- "Key methods" lists miss newly added methods
- "5 abstract methods" becomes wrong when a 6th is added
- Field counts on large dataclasses drift silently

## Solutions

### 1. Use Source Pointers

Instead of listing methods, point to the source:

```markdown
See `PlanDataProvider` abstract methods in
`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py`
```

### 2. Avoid Numeric Counts

Instead of "5 abstract methods", write:

```markdown
Key abstract methods include:

- `fetch_plans()` - retrieves plan list
- `close_plan()` - closes a plan
- ... (see ABC for complete list)
```

### 3. Programmatic Verification

For critical counts, add verification commands:

```bash
# Verify method count
rg "abstractmethod" abc.py | wc -l
```

## Related Documentation

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) — the 5-place update pattern
- [Documentation Specificity Guidelines](../documentation/specificity-guidelines.md) — what belongs in docs vs source
