---
title: erk-impl Workflow Patterns
read_when:
  - "modifying erk-impl workflow"
  - "adding cleanup steps to GitHub Actions"
  - "working with git reset in workflows"
tripwires:
  - action: "running `git reset --hard` in workflows after staging cleanup"
    warning: "Verify all cleanup changes are committed BEFORE reset; staged changes without commit will be silently discarded."
---

# erk-impl Workflow Patterns

This document covers critical patterns for the erk-impl GitHub Actions workflow, with particular focus on cleanup operations and step ordering.

## Critical: Cleanup Before Reset

**The Most Important Rule:** Commit cleanup changes BEFORE any `git reset --hard` operation.

### Why This Matters

`git reset --hard` discards all staged but uncommitted changes. In the erk-impl workflow, this manifests as:

1. Workflow stages `.worker-impl/` deletion with `git add`
2. Later step runs `git reset --hard` (e.g., for conflict resolution)
3. The staged deletion is silently discarded
4. `.worker-impl/` artifacts appear in the final PR

### Correct Pattern

```yaml
# 1. First: Commit and push cleanup
- name: Clean up .worker-impl/
  run: |
    if [ -d .worker-impl/ ]; then
      git rm -rf .worker-impl/
      git commit -m "Remove .worker-impl/ after implementation"
      git push
    fi

# 2. Then: Any operations that might reset
- name: Sync with remote
  run: |
    git fetch origin
    git reset --hard origin/$BRANCH  # Safe now - cleanup already pushed
```

### Incorrect Pattern (Silent Failure)

```yaml
# WRONG: Staging without commit before reset
- name: Stage cleanup
  run: git rm -rf .worker-impl/ && git add -A

- name: Sync with remote
  run: git reset --hard origin/$BRANCH # Discards the staged cleanup!
```

## Multi-Layer Cleanup Resilience

The erk-impl workflow uses multiple cleanup mechanisms for reliability:

| Layer               | Mechanism                    | Reliability       |
| ------------------- | ---------------------------- | ----------------- |
| 1. Agent cleanup    | Claude's /erk:plan-implement | Non-deterministic |
| 2. Workflow staging | `git rm` + `git add`         | Fragile           |
| 3. Workflow commit  | Dedicated cleanup step       | Deterministic     |

**Lesson learned:** Only layer 3 (dedicated commit step) is reliable. Agent behavior varies based on context limits and interpretation. Staging without commit is fragile due to reset interactions.

## Step Output Validation

When composing conditions across multiple workflow steps, validate each reference:

### Common Validation Errors

1. **Typos in step IDs**: `steps.implentation.outcome` vs `steps.implementation.outcome`
2. **Missing step IDs**: Step doesn't have an `id:` field
3. **Wrong output key**: `steps.foo.outputs.result` when step outputs `outcome`

### Validation Checklist

Before using a compound condition:

- [ ] Each step referenced has an `id:` field
- [ ] Step ID spelling matches exactly (case-sensitive)
- [ ] Output key exists (use `steps.*.outcome` for job status)
- [ ] Condition logic handles all states (success/failure/skipped)

### Example: Correct Step Reference

```yaml
- name: Run implementation
  id: impl
  run: |
    # ... implementation logic
    echo "has_changes=true" >> $GITHUB_OUTPUT

- name: Handle results
  if: steps.impl.outcome == 'success' && steps.impl.outputs.has_changes == 'true'
  run: |
    # Only runs when impl succeeded AND has changes
```

## Workflow Step Ordering

Critical ordering dependencies in erk-impl:

```
1. Checkout & setup
2. Find/create PR
3. Implementation (Claude)
4. Commit implementation changes  ← Must happen before cleanup
5. Clean up .worker-impl/         ← Must commit before any reset
6. Push changes
7. Mark PR ready
```

**Key insight:** Steps 4-6 must maintain this exact order. Interleaving cleanup with implementation commits causes silent failures.

## Related Documentation

- [erk-impl Change Detection](erk-impl-change-detection.md) - Detecting what changed during implementation
- [GitHub Actions Output Patterns](github-actions-output-patterns.md) - Multi-line outputs and step communication
