---
title: GitHub Actions Label Filtering Reference
read_when:
  - debugging why label-based CI gating isn't working
  - implementing label-based workflow conditions
  - confused about .*.name syntax vs array filtering
tripwires:
  - action: "using Python constants in GitHub Actions workflows"
    warning: "GitHub Actions cannot interpolate Python constants - label strings must be hardcoded in YAML"
  - action: "setting up label filtering for push events"
    warning: "always use negation (!contains) for safe defaults on push events without PR context"
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
if: contains(github.event.pull_request.labels.*.name, 'erk-plan-review')
```

| Event Type    | labels.\*.name value | Result  | Job runs? | Issue                       |
| ------------- | -------------------- | ------- | --------- | --------------------------- |
| PR with label | `["erk-plan-..."]`   | `true`  | Yes       | Intended: label present     |
| PR no label   | `[]`                 | `false` | No        | **WRONG: should run CI**    |
| Push event    | `[]` (null context)  | `false` | No        | **WRONG: breaks branch CI** |

**Correct approach:** Use negation (`!contains()`) to invert the logic:

```yaml
# CORRECT - safe defaults
if: !contains(github.event.pull_request.labels.*.name , 'erk-plan-review')
```

| Event Type    | labels.\*.name value | Result  | Job runs? | Behavior                   |
| ------------- | -------------------- | ------- | --------- | -------------------------- |
| PR with label | `["erk-plan-..."]`   | `false` | No        | Intended: skip plan review |
| PR no label   | `[]`                 | `true`  | Yes       | Intended: run normal CI    |
| Push event    | `[]` (null context)  | `true`  | Yes       | Safe: run CI when unsure   |

**The insight:** Negation makes "run CI" the default, ensuring push events aren't silently skipped.

## The Synchronization Trap

**Problem:** GitHub Actions workflows are YAML, label definitions are Python constants. There's no way to interpolate Python values into YAML.

<!-- Source: src/erk/cli/constants.py, PLAN_REVIEW_LABEL -->

See `PLAN_REVIEW_LABEL` in `src/erk/cli/constants.py` for the Python constant.

<!-- Source: .github/workflows/ci.yml, check-submission job if condition -->
<!-- Source: .github/workflows/code-reviews.yml, discover job if condition -->

See job-level `if` conditions in `.github/workflows/ci.yml` and `.github/workflows/code-reviews.yml` for hardcoded label strings.

**Why this matters:**

- Renaming a label in Python doesn't update YAML workflows
- YAML label strings must be manually synchronized with Python constants
- No CI check can detect the mismatch (different languages)

**When renaming labels:** See `docs/learned/ci/label-rename-checklist.md` for the full synchronization procedure.

## The .\*.name Syntax

**What it is:** GitHub Actions' array property extraction operator. Given an array of objects, `.*.property` extracts that property from each object into a new array.

**Why it's confusing:** It looks like a glob pattern but it's actually array manipulation.

Input structure:

```json
{
  "labels": [
    { "name": "bug", "color": "d73a4a" },
    { "name": "erk-plan-review", "color": "5319e7" }
  ]
}
```

Operation result:

- `labels` → `[{name: "bug", ...}, {name: "erk-plan-review", ...}]`
- `labels.*.name` → `["bug", "erk-plan-review"]`
- `contains(["bug", "erk-plan-review"], "erk-plan-review")` → `true`

The `.*` is GitHub's syntax, not standard JSON path notation.

## Defense-in-Depth Pattern

**Problem:** Job-level `if` conditions can't access PR labels on push events (no `pull_request` context).

**Solution:** Two-layer checks:

1. **Job level** — Fast path for PR events with label context
2. **Step level** — API query for push events to fetch labels via gh CLI

<!-- Source: .github/workflows/ci.yml, autofix job lines 148-228 -->

See the `autofix` job in `.github/workflows/ci.yml` for the complete pattern:

- Job-level `if` uses `github.event.pull_request.labels.*.name` (fast, PR events only)
- "Check erk-plan-review label" step uses `gh api` to query labels (slower, works on push events)

**Why both layers:**

- Job-level check skips the entire job for labeled PRs (saves CI minutes)
- Step-level check handles push events where job-level check can't access labels
- Double-checking prevents label bypass via direct branch pushes

## When to Use This Pattern

| Scenario                             | Use Label Filtering? | Notes                                           |
| ------------------------------------ | -------------------- | ----------------------------------------------- |
| Skip CI for plan review PRs          | Yes                  | Standard usage (ci.yml, code-reviews.yml)       |
| Skip autofix for submission-only PRs | Yes                  | Autofix job uses both job and step-level checks |
| Conditional workflow dispatch        | No                   | Use workflow inputs instead                     |
| Matrix job filtering                 | No                   | Filter in discover job, not each matrix element |
| Filtering within a composite action  | No                   | Composite actions can't access event context    |

## Related Documentation

- [Workflow Gating Patterns](workflow-gating-patterns.md) - Complete workflow gating strategy
- [GitHub Actions Label Queries](github-actions-label-queries.md) - Push event label checks via API
- [CI Label Rename Checklist](label-rename-checklist.md) - Synchronization procedures

## Attribution

Pattern established in PR #6243. Reference documentation created from PR #6400 (label rename fix).
