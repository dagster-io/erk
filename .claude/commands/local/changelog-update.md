---
description: Sync CHANGELOG.md unreleased section with commits since last update
---

# /local:changelog-update

Brings the CHANGELOG.md Unreleased section up-to-date with commits merged to master.

> **Note:** Run this regularly during development. At release time, use `/local:changelog-release`.

## Usage

```bash
/local:changelog-update
```

## What It Does

1. Reads the "As of" marker in the Unreleased section (adds one if missing)
2. Finds commits on master since that marker
3. Categorizes commits and presents proposal for user review
4. Updates changelog only after user approval
5. Always updates the "As of" marker to current HEAD (even if no new entries)

---

## Agent Instructions

### Phase 1: Launch Categorization Agent

Launch a subagent to fetch commits, read the CHANGELOG, and categorize:

```
Task(
  subagent_type: "general-purpose",
  description: "Categorize changelog commits",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/changelog/commit-categorizer.md`
)
```

### Phase 2: Parse Result

Parse the agent's output by examining the `STATUS` line:

- **`STATUS: ERROR`** - Display the `ERROR_MESSAGE` and stop.
- **`STATUS: NO_COMMITS`** - Update the "As of" line in CHANGELOG.md to the `HEAD_COMMIT` value. Report "CHANGELOG.md is already up-to-date. Updated marker to {HEAD_COMMIT}." and stop.
- **`STATUS: OK`** - Extract the proposal text after `---PROPOSAL---` and proceed to Phase 3.

### Phase 3: Present Proposal for Review

**CRITICAL: Do NOT edit the changelog yet. Present the proposal and wait for user approval.**

Display the proposal text from the agent verbatim. The proposal includes categorized entries, filtered commits, low-confidence flags, and asks the user to approve or adjust.

Wait for the user to:

1. Approve as-is
2. Request adjustments to categorizations
3. Request rephrased descriptions
4. Include or exclude specific commits

### Phase 4: Update CHANGELOG.md (After Approval)

Only proceed after the user confirms or provides adjustments.

Update the Unreleased section:

1. **Update "As of" line** to current HEAD commit hash
2. **Add new entries** under appropriate category headers
3. **Preserve existing entries** - do not remove or modify them
4. **Create category headers** only if they have new entries

Category order (if present):

1. Major Changes
2. Added
3. Changed
4. Fixed
5. Removed

If a category header already exists, append new entries below existing ones.

### Phase 5: Report

After successful update:

```
Updated CHANGELOG.md:
- Processed {n} commits
- Added {m} entries to: {categories}
- Now as of {commit}
```

### Entry Format

Format each entry as:

```markdown
- Brief user-facing description (commit_hash)
```

Guidelines:

- Focus on **user benefit**, not implementation details
- Start with a verb (Add, Fix, Improve, Remove, Move, Migrate)
- Be concise but clear (1 sentence)
- Include the short commit hash in parentheses
- Add notes for entries that may cause user-visible issues (e.g., "note: this may cause hard failures, please report if encountered")
