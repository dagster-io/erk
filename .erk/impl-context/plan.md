# Plan: Improve pr-triage command output format

## Context

During a triage session, the original tiered-section output format was immediately replaced by the user with a single flat table sorted by last updated, with tier as a column. The user also requested longer, more readable tier codes instead of terse abbreviations. This plan codifies those preferences into the command itself.

## File to modify

`/Users/schrockn/code/erk/.claude/commands/local/pr-triage.md`

## Changes

### 1. Rename tier codes to readable labels

| Tier | Old Code | New Code | Category |
|------|----------|----------|----------|
| 1 | (none/number) | `bug-fix` | Bug fixes |
| 2 | (none/number) | `safe-tweak` | Small safe changes |
| 3 | (none/number) | `cleanup` | Dead code removal / simplification |
| 4 | (none/number) | `new-feat` | New features / large changes |
| 5 | (none/number) | `stale` | Close candidates |

Update the Phase 2 classification table to include a "Code" column with these labels.

### 2. Change output format: single table instead of per-tier sections

Replace the Phase 5 output template (lines 66-100) with a single flat table ordered by Last Updated descending, with Tier as a column:

```
## PR Triage Analysis

**Date:** YYYY-MM-DD | **Open PRs:** N | **Passing CI:** N | **Failing CI:** N

| PR | Title | Tier | CI | Size | Draft | Last Updated |
|----|-------|------|----|------|-------|--------------|
(all PRs, ordered by Last Updated descending)

**Legend:** bug-fix | safe-tweak | cleanup | new-feat | stale
```

### 3. Remove Phase 4 (within-tier ordering)

Since the table is now sorted by Last Updated (not grouped by tier), the within-tier ordering rules in Phase 4 are no longer needed. Remove that section.

### 4. Shorten CI status labels

Update Phase 3 to use shorter CI labels to keep the table compact:
- `PASSING` → `PASS`
- `FAILING` → `FAIL`
- `PENDING` → `PEND`
- `UNKNOWN` → `UNK`

### 5. Use `Nd ago` for staleness display

Specify that Last Updated should display as `Nd ago` (e.g. `0d ago`, `3d ago`) for scannability, rather than raw dates.

## Verification

Run `/local:pr-triage` after the edit and confirm:
- Output is a single flat table sorted by last updated
- Tier column uses the new readable codes
- CI column uses short codes
- Last Updated shows `Nd ago` format
