---
title: GitHub Actions Label Filtering Reference
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
read_when:
  - debugging why label-based CI gating isn't working
  - implementing label-based workflow conditions
  - confused about .*.name syntax vs array filtering
tripwires:
  - action: GitHub Actions cannot interpolate Python constants
    warning: label strings must be hardcoded in YAML
  - action: using label-based gating
    warning:
      Always use negation (!contains) for safe defaults on push events without
      PR context
---

# GitHub Actions Label Filtering Reference

## Why Label Filtering Is Non-Obvious

GitHub Actions label checks are counterintuitive because:

1. **The syntax hides array operations** — `.*.name` is property extraction, not dot notation
2. **Event context matters** — `pull_request.labels` is available only on PR events, not push events
3. **Negation determines safe defaults** — `!contains()` ensures push events run CI, `contains()` would skip them

This document explains the WHY behind the pattern, not the syntax itself.

## The Safe Default Problem

**Problem:** CI must handle both PR events (with label context) and push events (no PR context).

**Wrong approach:** Use `contains()` to check for exclusion labels:

```yaml
# WRONG - breaks push events
if: contains(github.event.pull_request.labels.*.name, 'skip-ci')
```

| Event Type    | labels.\*.name value | Result  | Job runs? | Issue                       |
| ------------- | -------------------- | ------- | --------- | --------------------------- |
| PR with label | `["skip-ci"]`        | `true`  | Yes       | Intended: label present     |
| PR no label   | `[]`                 | `false` | No        | **WRONG: should run CI**    |
| Push event    | `[]` (null context)  | `false` | No        | **WRONG: breaks branch CI** |

**Correct approach:** Use negation (`!contains()`) to invert the logic:

```yaml
# CORRECT - safe defaults
if: !contains(github.event.pull_request.labels.*.name, 'skip-ci')
```

| Event Type    | labels.\*.name value | Result  | Job runs? | Behavior                |
| ------------- | -------------------- | ------- | --------- | ----------------------- |
| PR with label | `["skip-ci"]`        | `false` | No        | Intended: skip CI       |
| PR no label   | `[]`                 | `true`  | Yes       | Intended: run normal CI |
| Push event    | `[]` (null context)  | `true`  | Yes       | Safe: run CI when unsure|

**The insight:** Negation makes "run CI" the default, ensuring push events aren't silently skipped.

## The .\*.name Syntax

**What it is:** GitHub Actions' array property extraction operator. Given an array of objects, `.*.property` extracts that property from each object into a new array.

**Why it's confusing:** It looks like a glob pattern but it's actually array manipulation.

Input structure:

```json
{
  "labels": [
    { "name": "bug", "color": "d73a4a" },
    { "name": "enhancement", "color": "5319e7" }
  ]
}
```

Operation result:

- `labels` → `[{name: "bug", ...}, {name: "enhancement", ...}]`
- `labels.*.name` → `["bug", "enhancement"]`
- `contains(["bug", "enhancement"], "bug")` → `true`

The `.*` is GitHub's syntax, not standard JSON path notation.

## When to Use This Pattern

| Scenario                            | Use Label Filtering? | Notes                                               |
| ----------------------------------- | -------------------- | --------------------------------------------------- |
| Skip CI for specific label          | Yes                  | Use `!contains()` at job level                      |
| Conditional workflow dispatch       | No                   | Use workflow inputs instead                         |
| Matrix job filtering                | No                   | Filter in the discover job, not each matrix element |
| Filtering within a composite action | No                   | Composite actions can't access event context        |

## Related Documentation

- [Workflow Gating Patterns](workflow-gating-patterns.md) - Complete workflow gating strategy
- [GitHub Actions Label Queries](github-actions-label-queries.md) - Push event label checks via API
