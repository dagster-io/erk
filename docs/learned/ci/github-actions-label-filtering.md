---
title: GitHub Actions Label Filtering Reference
read_when:
  - understanding the .*.name syntax for label checks
  - debugging why label-based CI gating isn't working
  - implementing label-based workflow conditions
---

# GitHub Actions Label Filtering Reference

Quick reference for the GitHub Actions label filtering pattern, explaining the syntax, semantics, and synchronization requirements.

## Core Pattern

```yaml
if: !contains(github.event.pull_request.labels.*.name , 'erk-plan-review')
```

### Syntax Breakdown

| Component                   | Meaning                                      | Example Value                                        |
| --------------------------- | -------------------------------------------- | ---------------------------------------------------- |
| `github.event.pull_request` | The pull request object in the event context | `{ "number": 123, "title": "...", "labels": [...] }` |
| `.labels`                   | Array of label objects                       | `[{ "name": "bug", "color": "..." }, ...]`           |
| `.*.name`                   | Extract `name` field from each label object  | `["bug", "enhancement"]`                             |
| `contains(array, value)`    | Check if array contains value                | `contains(["bug"], "bug")` → `true`                  |
| `!contains(...)`            | Negation - true if value NOT in array        | `!contains(["bug"], "enhancement")` → `true`         |

### Why `.*.name` Syntax

The `.*` is GitHub Actions' array property extraction syntax:

- **Input:** Array of objects with a `name` property
- **Output:** Array of just the `name` values
- **Alternative notation:** Some documentation calls this "filter" or "map" operation

```yaml
# labels array structure
[
  { "name": "bug", "color": "d73a4a" },
  { "name": "enhancement", "color": "a2eeef" }
]

# labels.*.name result
["bug", "enhancement"]
```

## Why Negation Matters

Using negation (`!contains`) is critical for safe defaults:

| Event Type       | `labels.*.name` value  | `contains()` result | `!contains()` result | Job runs?          |
| ---------------- | ---------------------- | ------------------- | -------------------- | ------------------ |
| PR with label    | `["erk-plan-review"]`  | `true`              | `false`              | No (intended)      |
| PR without label | `[]`                   | `false`             | `true`               | Yes (intended)     |
| Push event       | `[]` (null PR context) | `false`             | `true`               | Yes (safe default) |

**Without negation** (`contains()` only):

- Push events would skip CI (empty array → `false` → job skipped)
- This breaks CI on direct branch pushes

**With negation** (`!contains()`):

- Push events run CI (empty array → `true` → job runs)
- Safe default: when in doubt, run CI

## Authoritative Label Definitions

Label names used in CI workflows should match Python constants defined in `src/erk/cli/constants.py`:

```python
PLAN_REVIEW_LABEL = "erk-plan-review"
```

However, GitHub Actions workflows **cannot interpolate Python constants**. The YAML files must contain hardcoded string literals:

```yaml
# CORRECT - hardcoded label string
if: !contains(github.event.pull_request.labels.*.name, 'erk-plan-review')

# WRONG - cannot interpolate Python constant
if: !contains(github.event.pull_request.labels.*.name, ${{ PLAN_REVIEW_LABEL }})
```

This creates a **synchronization requirement**: when label names change, both the Python constant AND all YAML workflow files must be updated.

## Synchronization Checklist

When renaming a label used in CI automation, follow the comprehensive checklist:

See [CI Label Rename Checklist](label-rename-checklist.md) for complete update procedures.

## Common Patterns

### Exclude labeled PRs

```yaml
if: !contains(github.event.pull_request.labels.*.name , 'erk-plan-review')
```

Use this to skip jobs for specific PR types.

### Combine with draft check

```yaml
if: |
  github.event.pull_request.draft != true &&
  !contains(github.event.pull_request.labels.*.name, 'erk-plan-review')
```

Ensure job only runs for ready, code-containing PRs.

### Defense-in-depth (job + step level)

```yaml
jobs:
  autofix:
    # Fast path - skip for pull_request events with label
    if: |
      (github.event_name != 'pull_request' ||
       !contains(github.event.pull_request.labels.*.name, 'erk-plan-review'))
    steps:
      # Required path - check labels for push events via API
      - name: Check erk-plan-review label
        run: |
          labels=$(gh api repos/${{ github.repository }}/pulls/$PR_NUMBER --jq '[.labels[].name] | join(",")')
          if echo "$labels" | grep -q "erk-plan-review"; then
            echo "has_label=true" >> $GITHUB_OUTPUT
          fi
```

See [GitHub Actions Label Queries](github-actions-label-queries.md) for the complete push event pattern.

## Related Documentation

- [GitHub Actions Workflow Gating Patterns](workflow-gating-patterns.md) - Complete workflow gating strategy
- [GitHub Actions Label Queries](github-actions-label-queries.md) - Push event label checks via API
- [CI Label Rename Checklist](label-rename-checklist.md) - Synchronization procedures

## Attribution

Pattern established in PR #6243. Reference documentation created from PR #6400 (label rename fix).
