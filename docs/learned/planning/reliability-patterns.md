---
title: Workflow Reliability Patterns
read_when:
  - "designing cleanup operations in workflows"
  - "choosing between agent vs workflow-native operations"
  - "implementing multi-layer failure resilience"
---

# Workflow Reliability Patterns

Patterns for building reliable automated workflows, with focus on deterministic vs non-deterministic operations.

## Deterministic vs Non-Deterministic Operations

### The Core Distinction

| Type              | Definition                                    | Reliability | Example                           |
| ----------------- | --------------------------------------------- | ----------- | --------------------------------- |
| Deterministic     | Same input always produces same output        | High        | Workflow step with explicit logic |
| Non-deterministic | Output varies based on context/interpretation | Low         | Agent behavior in Claude          |

### When to Use Each

**Use deterministic (workflow-native) for:**

- Critical cleanup operations
- State mutations that must complete
- Security-sensitive operations
- Operations that can't be easily retried

**Use non-deterministic (agent-dependent) for:**

- Creative/generative tasks
- Tasks requiring contextual interpretation
- Tasks where partial success is acceptable
- Operations with built-in retry mechanisms

## Multi-Layer Failure Mode Design

For critical operations, implement multiple independent layers:

### Example: `.worker-impl/` Cleanup

```
Layer 1: Agent cleanup (non-deterministic)
    ↓ (might skip due to context limits)
Layer 2: Workflow staging (fragile)
    ↓ (might be undone by git reset)
Layer 3: Dedicated workflow step (deterministic)
    ↓ (reliable - commits and pushes)
```

### Layer Reliability Analysis

| Layer | Mechanism                              | Failure Mode                      |
| ----- | -------------------------------------- | --------------------------------- |
| 1     | Agent instruction in plan-implement    | Context limits, misinterpretation |
| 2     | `git add` followed by later commit     | Reset discards staged changes     |
| 3     | Dedicated commit step before any reset | None (if step runs)               |

**Key insight:** Only Layer 3 is truly reliable. Layers 1 and 2 serve as defense-in-depth but cannot be the sole mechanism for critical operations.

## Decision Framework

When implementing automated cleanup or state changes:

### Question 1: Is this operation critical?

- **Yes**: Must be workflow-native (deterministic)
- **No**: Can be agent-dependent if convenient

### Question 2: Can partial failure be detected?

- **Yes**: Agent-dependent may be acceptable with retry logic
- **No**: Must be workflow-native with explicit verification

### Question 3: Does operation require interpretation?

- **Yes**: Agent-dependent, but add workflow-native fallback
- **No**: Prefer workflow-native for predictability

## Pattern: Commit-Before-Reset

When mixing cleanup with operations that might reset:

```yaml
# CORRECT: Commit cleanup before any reset possibility
- name: Commit cleanup
  run: |
    git rm -rf artifacts/
    git commit -m "Clean up artifacts"
    git push

- name: Sync (might reset)
  run: git fetch && git reset --hard origin/main

# INCORRECT: Stage cleanup, reset later undoes it
- name: Stage cleanup
  run: git rm -rf artifacts/

- name: Sync (undoes staging)
  run: git reset --hard origin/main # Staged changes lost!
```

## Pattern: Verification After Critical Operations

Don't assume operations succeeded. Verify:

```yaml
- name: Clean up artifacts
  run: |
    git rm -rf artifacts/
    git commit -m "Clean up"
    git push

- name: Verify cleanup
  run: |
    if [ -d artifacts/ ]; then
      echo "ERROR: Cleanup failed - artifacts still present"
      exit 1
    fi
```

## Related Documentation

- [erk-impl Workflow Patterns](../ci/erk-impl-workflow-patterns.md) - Specific erk workflow patterns
- [erk-impl Change Detection](../ci/erk-impl-change-detection.md) - Detecting changes in workflows
