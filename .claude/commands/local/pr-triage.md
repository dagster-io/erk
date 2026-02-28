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

| Tier | Code         | Category                           | Heuristics                                                                                 |
| ---- | ------------ | ---------------------------------- | ------------------------------------------------------------------------------------------ |
| 1    | `bug-fix`    | Bug Fixes                          | Title contains "fix" AND corrects behavior (not lint/typo/docs fixes)                      |
| 2    | `safe-tweak` | Small Safe Changes                 | <=30 total lines changed (additions+deletions) OR purely docs/config/observability changes |
| 3    | `cleanup`    | Dead Code Removal / Simplification | deletions > 2x additions AND title contains remove/simplify/delete/clean                   |
| 4    | `new-feat`   | New Features / Large Changes       | additions >> deletions, new capabilities, large refactors                                  |
| 5    | `stale`      | Stale / Empty / Close Candidates   | 0 changes, OR draft >30 days since updatedAt, OR superseded                                |

**Label awareness:** Account for erk-specific labels (`erk-plan`, `erk-pr`, `erk-learn`, `erk-planned-pr`). Plan PRs (`erk-plan`) are tracking issues, not code PRs - classify them in Tier 5 as close candidates if they have 0 code changes.

### Phase 3: Annotate Each PR

For each PR, derive:

- **CI status** from `statusCheckRollup`: PASS / FAIL / PEND / UNK
  - PASS: all checks have conclusion "SUCCESS" or "NEUTRAL"
  - FAIL: any check has conclusion "FAILURE" or "CANCELLED"
  - PEND: any check has state "PENDING" or "QUEUED" and none are failing
  - UNK: no checks or empty statusCheckRollup
- **Size**: `+additions/-deletions (N files)`
- **Last Updated**: display as `Nd ago` (e.g. `0d ago`, `3d ago`) for scannability

### Phase 4: Present Analysis

Output the analysis as a single flat table ordered by Last Updated descending (most recently updated first), with Tier as a column:

```
## PR Triage Analysis

**Date:** YYYY-MM-DD | **Open PRs:** N | **Passing CI:** N | **Failing CI:** N

| PR | Title | Tier | CI | Size | Draft | Last Updated |
|----|-------|------|----|------|-------|--------------|
(all PRs, ordered by Last Updated descending)

**Legend:** bug-fix | safe-tweak | cleanup | new-feat | stale

### Recommended Landing Order
1. **#NNN** - Title -- rationale
2. **#NNN** - Title -- rationale
...

### PRs to Consider Closing
- **#NNN** - Title -- reason
```

### Phase 5: User Interaction

After presenting the analysis, ask the user what they want to act on:

- Land specific PRs
- Close candidates
- Review specific PRs in detail

**CRITICAL:** Do NOT auto-close or auto-land anything. All actions require explicit user approval.
