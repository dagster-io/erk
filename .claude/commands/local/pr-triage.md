---
description: Analyze and prioritize open PRs for stability-focused landing order
---

# /local:pr-triage

Analyzes all open PRs, classifies them into priority tiers, and recommends a stability-focused landing order.

## Usage

```bash
/local:pr-triage
```

---

## Agent Instructions

### Phase 1: Data Collection

Fetch all open PRs with metadata:

```bash
gh pr list --state open --limit 100 --json number,title,labels,isDraft,additions,deletions,changedFiles,statusCheckRollup,updatedAt,createdAt,author
```

Store the result for analysis.

### Phase 2: Classify Each PR

Assign each PR to exactly one tier (highest applicable wins):

| Tier | Category                           | Heuristics                                                                                 |
| ---- | ---------------------------------- | ------------------------------------------------------------------------------------------ |
| 1    | Bug Fixes                          | Title contains "fix" AND corrects behavior (not lint/typo/docs fixes)                      |
| 2    | Small Safe Changes                 | <=30 total lines changed (additions+deletions) OR purely docs/config/observability changes |
| 3    | Dead Code Removal / Simplification | deletions > 2x additions AND title contains remove/simplify/delete/clean                   |
| 4    | New Features / Large Changes       | additions >> deletions, new capabilities, large refactors                                  |
| 5    | Stale / Empty / Close Candidates   | 0 changes, OR draft >30 days since updatedAt, OR superseded                                |

**Label awareness:** Account for erk-specific labels (`erk-plan`, `erk-pr`, `erk-learn`, `erk-planned-pr`). Plan PRs (`erk-plan`) are tracking issues, not code PRs - classify them in Tier 5 as close candidates if they have 0 code changes.

### Phase 3: Annotate Each PR

For each PR, derive:

- **CI status** from `statusCheckRollup`: PASSING / FAILING / PENDING / UNKNOWN
  - PASSING: all checks have conclusion "SUCCESS" or "NEUTRAL"
  - FAILING: any check has conclusion "FAILURE" or "CANCELLED"
  - PENDING: any check has state "PENDING" or "QUEUED" and none are failing
  - UNKNOWN: no checks or empty statusCheckRollup
- **Size**: `+additions/-deletions (N files)`
- **Staleness**: days since `updatedAt`

### Phase 4: Within-Tier Ordering

Within each tier, order PRs by:

1. CI passing before failing
2. Smaller (fewer total lines) before larger
3. Non-draft before draft
4. More recently updated before staler

### Phase 5: Present Analysis

Output the analysis in this format:

```
## PR Triage Analysis

**Date:** YYYY-MM-DD | **Open PRs:** N | **Passing CI:** N | **Failing CI:** N

### Tier 1: Bug Fixes
| PR | Title | CI | Size | Draft | Last Updated |
|...

### Tier 2: Small Safe Changes
| PR | Title | CI | Size | Draft | Last Updated |
|...

### Tier 3: Dead Code Removal / Simplification
| PR | Title | CI | Size | Draft | Last Updated |
|...

### Tier 4: New Features / Large Changes
| PR | Title | CI | Size | Draft | Last Updated |
|...

### Tier 5: Stale / Empty / Close Candidates
| PR | Title | CI | Size | Draft | Last Updated | Reason |
|...

### Recommended Landing Order
1. **#NNN** - Title -- rationale
2. **#NNN** - Title -- rationale
...

### PRs to Consider Closing
- **#NNN** - Title -- reason
```

### Phase 6: User Interaction

After presenting the analysis, ask the user what they want to act on:

- Land specific PRs
- Close candidates
- Review specific PRs in detail

**CRITICAL:** Do NOT auto-close or auto-land anything. All actions require explicit user approval.
