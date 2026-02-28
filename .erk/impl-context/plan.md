# Plan: Create `/local:pr-triage` Command

## Context

We manually analyzed open PRs earlier in this conversation to prioritize bug fixes and stabilization work. The user wants this analysis to be reusable as a slash command they can invoke at any time.

## What to Create

**Single file:** `.claude/commands/local/pr-triage.md`

This follows the established local command pattern (see `audit-branches.md`, `audit-plans.md`, `code-stats.md`). No additional reference files needed — the classification heuristics fit within the command file itself.

## Command Design

### Frontmatter

```yaml
---
description: Analyze and prioritize open PRs for stability-focused landing order
---
```

No `context: fork` or `agent` — this runs in the main conversation so the user can discuss results and act on recommendations.

### Phases

**Phase 1: Data Collection**
- Single `gh pr list` call with `--json number,title,labels,isDraft,additions,deletions,changedFiles,statusCheckRollup,updatedAt,createdAt,author`
- `--limit 100` to capture all open PRs
- No `body` field (too large for bulk fetch; fetch per-PR only if classification is ambiguous)

**Phase 2: Classify Each PR**

Assign each PR to exactly one tier (highest applicable):

| Tier | Category | Heuristics |
|------|----------|------------|
| 1 | Bug Fixes | Title contains "fix" + corrects behavior (not lint/typo/docs fixes) |
| 2 | Small Safe Changes | <=30 total lines OR purely docs/config/observability |
| 3 | Dead Code Removal / Simplification | deletions > 2x additions, title says remove/simplify/delete |
| 4 | New Features / Large Changes | additions >> deletions, new capabilities, large refactors |
| 5 | Stale / Empty / Close Candidates | 0 changes, draft >30 days stale, superseded |

**Phase 3: Annotate**

For each PR derive:
- CI status from `statusCheckRollup`: PASSING / FAILING / PENDING / UNKNOWN
- Size: `+additions/-deletions (N files)`
- Staleness: days since `updatedAt`

**Phase 4: Present Analysis**

Output format:

```
## PR Triage Analysis

**Date:** YYYY-MM-DD | **Open PRs:** N | **Passing CI:** N | **Failing CI:** N

### Tier 1: Bug Fixes
| PR | Title | CI | Size | Draft | Last Updated |
...

### Tier 2: Small Safe Changes
...

### Tier 3: Dead Code Removal / Simplification
...

### Tier 4: New Features / Large Changes
...

### Tier 5: Stale / Empty / Close Candidates
| PR | Title | CI | Size | Draft | Last Updated | Reason |
...

### Recommended Landing Order
1. **#NNN** - Title -- rationale
...

### PRs to Consider Closing
- **#NNN** - Title -- reason
```

**Phase 5: User Interaction**

Ask user what to act on (land specific PRs, close candidates, etc.). Do NOT auto-close or auto-land anything.

### Within-Tier Ordering Rules

1. CI passing before failing
2. Smaller before larger
3. Non-draft before draft
4. Fresher before staler

### Label Context

Include awareness of erk-specific labels (`erk-plan`, `erk-pr`, `erk-learn`, `erk-planned-pr`) so classification accounts for plan PRs vs regular PRs.

## Verification

1. Run `/local:pr-triage` and confirm it produces a categorized table
2. Verify the CI status derivation works (check a known-passing and known-failing PR)
3. Verify close candidates are flagged with reasons
4. Confirm the command does NOT take any destructive actions without user approval
