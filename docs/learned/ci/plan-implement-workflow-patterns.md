---
title: erk-impl Workflow Patterns
read_when:
  - "modifying erk-impl workflow"
  - "adding cleanup steps to GitHub Actions"
  - "working with git reset in workflows"
tripwires:
  - action: "running `git reset --hard` in workflows after staging cleanup"
    warning: "Verify all cleanup changes are committed BEFORE reset; staged changes without commit will be silently discarded."
  - action: "resolving git rebase modify/delete conflicts using merge-style terminology"
    warning: "In rebase, 'them' = upstream (opposite to merge). For modify/delete conflicts where the file was deleted upstream, use `git rm <file>` on the conflicted staged files, then `git rebase --continue`. Do not use `git checkout --theirs` which has inverted semantics during rebase."
    score: 5
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
---

# erk-impl Workflow Patterns

This document covers critical patterns for the erk-impl GitHub Actions workflow, with particular focus on cleanup operations and step ordering.

## Critical: Cleanup Before Reset

**The Most Important Rule:** Commit cleanup changes BEFORE any `git reset --hard` operation.

### Why This Matters

`git reset --hard` discards all staged but uncommitted changes. In the erk-impl workflow, this manifests as:

1. Workflow stages `.erk/impl-context/` deletion with `git add`
2. Later step runs `git reset --hard` (e.g., for conflict resolution)
3. The staged deletion is silently discarded
4. `.erk/impl-context/` artifacts appear in the final PR

### Correct Pattern

```yaml
# 1. First: Commit and push cleanup
- name: Clean up .erk/impl-context/
  run: |
    if [ -d .erk/impl-context/ ]; then
      git rm -rf .erk/impl-context/
      git commit -m "Remove .erk/impl-context/ after implementation"
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
  run: git rm -rf .erk/impl-context/ && git add -A

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
5. Clean up .erk/impl-context/   ← Must commit before any reset
6. Push changes
7. Mark PR ready
```

**Key insight:** Steps 4-6 must maintain this exact order. Interleaving cleanup with implementation commits causes silent failures.

## Branch State Consistency

### Race Condition

The plan-implement workflow has a timing issue: the plan job may push commits to the branch after the implement job checks it out. This means the implement job's checkout (from `github.sha`) can be behind the remote tip.

### Fix: Reset After Checkout

```yaml
- name: Checkout implementation branch
  run: |
    git checkout "$BRANCH_NAME"
    git fetch origin "$BRANCH_NAME"
    git reset --hard "origin/$BRANCH_NAME"
```

**Source**: `.github/workflows/plan-implement.yml` (implement job checkout step)

This is safe because the implement job has no local work to lose at this point — it's the first operation after checkout. The pattern ensures the implement job starts with the exact state the plan job left on the remote.

### Pattern: Checkout → Fetch → Reset

For workflow-dispatched branches where another job may have pushed commits:

1. `git checkout` — switch to the branch
2. `git fetch origin` — get latest remote state
3. `git reset --hard origin/$BRANCH` — sync local to remote tip

This pattern only applies at the start of a job, before any local work has been done.

## Related Documentation

- [GitHub Actions Output Patterns](github-actions-output-patterns.md) - Multi-line outputs and step communication
