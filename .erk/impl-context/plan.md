# Plan: Fix Major Changes overuse in changelog categorizer

## Context

During a `/local:changelog-update` run, the commit-categorizer agent classified a Graphite tracking bug fix (two related commits) as a "Major Change" — because the Roll-Up Detection section explicitly says to consolidate related commits into "a single Major Change entry." The user correctly noted that Major Changes should be rare and not forced; most releases won't have any.

The root cause is in two places in `commit-categorizer.md`:
1. Roll-Up Detection section defaults roll-ups to Major Changes
2. Output format template says "Suggest consolidating into single Major Change"

## Changes

**File:** `.claude/agents/changelog/commit-categorizer.md`

### 1. Roll-Up Detection section (lines ~218–240)

Change the framing so roll-ups consolidate into the *appropriate category*, not automatically into Major Changes.

**Current:**
```
When multiple commits are part of a larger initiative, group them under a single Major Change entry:
```

**Replace with:**
```
When multiple commits are part of a larger initiative, group them under a single entry in the appropriate category (Added, Changed, Fixed, or Removed). Only elevate to Major Changes if the consolidated initiative would independently qualify as a major change.
```

**Current examples section:**
```
**Roll-up examples:**

- 5+ commits about "kit" removal -> "Eliminate kit infrastructure entirely"
- 3+ commits about "artifact sync" -> "Add unified artifact distribution system"
- Multiple "objective skill" commits -> single entry or filter entirely
```

Add category guidance to each example:
```
**Roll-up examples:**

- 5+ commits about "kit" removal -> single Removed entry: "Eliminate kit infrastructure entirely"
- 3+ commits about "artifact sync" -> single Added entry: "Add unified artifact distribution system"
- Multiple bug fix commits on same subsystem -> single Fixed entry
- Multiple "objective skill" commits -> single entry or filter entirely
```

### 2. Output format template (lines ~234–238)

**Current:**
```
**Detected Roll-Up:** {n} commits appear related to "{topic}"
Suggest consolidating into single Major Change: "{proposed description}"
Commits: {list of hashes}
```

**Replace with:**
```
**Detected Roll-Up:** {n} commits appear related to "{topic}"
Suggest consolidating into single {Category} entry: "{proposed description}"
Commits: {list of hashes}
```

### 3. Add explicit rarity guidance to Major Changes section (after line ~103)

After the existing `**IMPORTANT: Major Changes must be USER-VISIBLE.**` paragraph, add:

```
**Not every release needs Major Changes.** Do not force a roll-up or a collection of fixes into this category just to have one. Only use Major Changes when the change is genuinely significant enough to warrant special attention in a release announcement.
```

## Files to modify

- `.claude/agents/changelog/commit-categorizer.md` — three edits described above

## Verification

Run `/local:changelog-update` on a branch where the unreleased commits are all bug fixes or improvements. Confirm the agent proposes no Major Changes section, and any multi-commit roll-ups appear under Added/Changed/Fixed.
